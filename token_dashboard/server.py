"""HTTP server: static frontend + JSON endpoints + SSE diff stream."""
from __future__ import annotations

import http.server
import json
import mimetypes
import queue
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .db import (
    overview_totals, expensive_prompts, project_summary,
    tool_token_breakdown, recent_sessions, session_turns,
    daily_token_breakdown, model_breakdown, skill_breakdown,
)
from .pricing import load_pricing, cost_for, get_plan, set_plan
from .tips import all_tips, dismiss_tip
from .scanner import scan_dir
from .skills import cached_catalog


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
PRICING_JSON = Path(__file__).resolve().parent.parent / "pricing.json"

MAX_POST_BYTES = 1_000_000  # 1 MB — we only accept tiny JSON bodies (plan, tip key)
MAX_LIMIT = 1000

# Per-client event queues. A single shared queue was wrong: queue.get() pops,
# so with two dashboard tabs open each scan event reached only one of them and
# the other silently stopped refreshing. Every stream now gets its own bounded
# queue, and a client too slow to drain it loses events instead of growing the
# server's memory without limit.
_subscribers: "set[queue.Queue[dict]]" = set()
_subscribers_lock = threading.Lock()
SUBSCRIBER_BACKLOG = 64


def publish(evt: dict) -> None:
    with _subscribers_lock:
        targets = list(_subscribers)
    for q in targets:
        try:
            q.put_nowait(evt)
        except queue.Full:
            pass  # slow reader — dropping is correct, the next scan re-reports


def _subscribe() -> "queue.Queue[dict]":
    q: "queue.Queue[dict]" = queue.Queue(maxsize=SUBSCRIBER_BACKLOG)
    with _subscribers_lock:
        _subscribers.add(q)
    return q


def _unsubscribe(q: "queue.Queue[dict]") -> None:
    with _subscribers_lock:
        _subscribers.discard(q)


def _send_json(handler, obj, status: int = 200) -> None:
    body = json.dumps(obj, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    if not getattr(handler, "head_only", False):
        handler.wfile.write(body)


def _send_error(handler, status: int, msg: str) -> None:
    _send_json(handler, {"error": msg}, status=status)


def _clamp_limit(raw, default: int) -> int:
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(v, MAX_LIMIT))


def _serve_static(handler, rel: str) -> None:
    rel = rel.lstrip("/")
    root = WEB_ROOT.resolve()
    p = (root / rel).resolve()
    # is_relative_to rather than a string startswith: the string form would let
    # a sibling directory named like the root (web-backup/) pass the check.
    if not p.is_relative_to(root) or not p.is_file():
        handler.send_response(404)
        handler.end_headers()
        return
    body = p.read_bytes()
    ctype, _ = mimetypes.guess_type(str(p))
    handler.send_response(200)
    handler.send_header("Content-Type", ctype or "application/octet-stream")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    if not getattr(handler, "head_only", False):
        handler.wfile.write(body)


def _host_allowed(handler) -> bool:
    """Reject requests whose Host header is not a loopback name.

    The dashboard binds to 127.0.0.1, but that alone does not stop a page on the
    open web from pointing a hostname it controls at 127.0.0.1 and reading this
    server's responses from the browser. Pinning the Host header to loopback
    closes that, and costs nothing for the intended local use.
    """
    host = (handler.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
    return host in ("", "localhost", "127.0.0.1", "::1", "0.0.0.0")


def build_handler(db_path: str, projects_dir: str):
    pricing = load_pricing(PRICING_JSON)

    class H(http.server.BaseHTTPRequestHandler):
        head_only = False

        def log_message(self, fmt, *args):
            pass

        def do_HEAD(self):
            self.head_only = True
            try:
                return self.do_GET()
            finally:
                self.head_only = False

        def do_GET(self):
            if not _host_allowed(self):
                return _send_error(self, 403, "invalid Host header")
            url = urlparse(self.path)
            qs = parse_qs(url.query or "")
            path = url.path
            since = qs.get("since", [None])[0]
            until = qs.get("until", [None])[0]
            if path in ("/", "/index.html"):
                return _serve_static(self, "index.html")
            if path.startswith("/web/"):
                return _serve_static(self, path[5:])
            if path == "/api/overview":
                totals = overview_totals(db_path, since, until)
                cost_usd = 0.0
                for m in model_breakdown(db_path, since, until):
                    c = cost_for(m["model"], m, pricing)
                    if c["usd"] is not None:
                        cost_usd += c["usd"]
                totals["cost_usd"] = round(cost_usd, 4)
                return _send_json(self, totals)
            if path == "/api/prompts":
                limit = _clamp_limit(qs.get("limit", ["50"])[0], 50)
                sort = qs.get("sort", ["tokens"])[0]
                rows = expensive_prompts(db_path, limit=limit, sort=sort, since=since, until=until)
                for r in rows:
                    # Only the cache-read component: the column this feeds is
                    # labelled "cache cost", not the turn's full price.
                    c = cost_for(r["model"], {
                        "input_tokens": 0, "output_tokens": 0,
                        "cache_read_tokens": r["cache_read_tokens"],
                        "cache_create_5m_tokens": 0, "cache_create_1h_tokens": 0,
                    }, pricing)
                    r["estimated_cost_usd"] = c["usd"]
                return _send_json(self, rows)
            if path == "/api/projects":
                return _send_json(self, project_summary(db_path, since, until))
            if path == "/api/tools":
                return _send_json(self, tool_token_breakdown(db_path, since, until))
            if path == "/api/sessions":
                return _send_json(self, recent_sessions(
                    db_path, limit=_clamp_limit(qs.get("limit", ["20"])[0], 20),
                    since=since, until=until,
                ))
            if path == "/api/daily":
                return _send_json(self, daily_token_breakdown(db_path, since, until))
            if path == "/api/skills":
                rows = skill_breakdown(db_path, since, until)
                catalog = cached_catalog(db_path=db_path)
                for r in rows:
                    info = catalog.get(r["skill"])
                    r["tokens_per_call"] = info["tokens"] if info else None
                return _send_json(self, rows)
            if path == "/api/by-model":
                rows = model_breakdown(db_path, since, until)
                for r in rows:
                    c = cost_for(r["model"], r, pricing)
                    r["cost_usd"] = c["usd"]
                    r["cost_estimated"] = c["estimated"]
                return _send_json(self, rows)
            if path.startswith("/api/sessions/"):
                sid = path.rsplit("/", 1)[1]
                return _send_json(self, session_turns(db_path, sid))
            if path == "/api/tips":
                return _send_json(self, all_tips(db_path, pricing=pricing))
            if path == "/api/plan":
                return _send_json(self, {"plan": get_plan(db_path), "pricing": pricing})
            if path == "/api/scan":
                n = scan_dir(projects_dir, db_path)
                return _send_json(self, n)
            if path == "/api/stream":
                return self._stream()
            self.send_response(404)
            self.end_headers()

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            if self.head_only:
                return
            q = _subscribe()
            try:
                while True:
                    try:
                        evt = q.get(timeout=15)
                        chunk = f"data: {json.dumps(evt, default=str)}\n\n".encode()
                    except queue.Empty:
                        chunk = b": ping\n\n"
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        return
            finally:
                _unsubscribe(q)

        def do_POST(self):
            if not _host_allowed(self):
                return _send_error(self, 403, "invalid Host header")
            url = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return _send_error(self, 400, "invalid Content-Length")
            if length < 0 or length > MAX_POST_BYTES:
                return _send_error(self, 413, f"body too large (max {MAX_POST_BYTES} bytes)")
            try:
                body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except json.JSONDecodeError:
                return _send_error(self, 400, "invalid JSON")
            if not isinstance(body, dict):
                return _send_error(self, 400, "body must be a JSON object")
            if url.path == "/api/plan":
                set_plan(db_path, body.get("plan", "api"))
                return _send_json(self, {"ok": True})
            if url.path == "/api/tips/dismiss":
                dismiss_tip(db_path, body.get("key", ""))
                return _send_json(self, {"ok": True})
            if url.path == "/api/scan":
                # The canonical verb for a scan, which mutates the database.
                # GET is kept above so existing curl habits keep working.
                return _send_json(self, scan_dir(projects_dir, db_path))
            self.send_response(404)
            self.end_headers()

    return H


def _scan_loop(db_path: str, projects_dir: str, interval: float = 30.0):
    while True:
        try:
            n = scan_dir(projects_dir, db_path)
            if n["messages"] > 0:
                publish({"type": "scan", "n": n, "ts": time.time()})
        except Exception as e:
            publish({"type": "error", "message": str(e)})
        time.sleep(interval)


def run(host: str, port: int, db_path: str, projects_dir: str):
    threading.Thread(target=_scan_loop, args=(db_path, projects_dir), daemon=True).start()
    H = build_handler(db_path, projects_dir)
    httpd = http.server.ThreadingHTTPServer((host, port), H)
    httpd.serve_forever()
