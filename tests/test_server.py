import http.server
import json
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from token_dashboard.db import init_db
from token_dashboard.server import build_handler


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "t.db")
        init_db(self.db)
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO messages (uuid, parent_uuid, session_id, project_slug, type, timestamp, model, input_tokens, output_tokens, cache_read_tokens, cache_create_5m_tokens, cache_create_1h_tokens, prompt_text, prompt_chars) VALUES ('u',NULL,'s','p','user','2026-04-19T00:00:00Z',NULL,0,0,0,0,0,'hi',2)")
            c.execute("INSERT INTO messages (uuid, parent_uuid, session_id, project_slug, type, timestamp, model, input_tokens, output_tokens, cache_read_tokens, cache_create_5m_tokens, cache_create_1h_tokens) VALUES ('a','u','s','p','assistant','2026-04-19T00:00:01Z','claude-haiku-4-5',1,1,0,0,0)")
            c.commit()
        self.port = _free_port()
        H = build_handler(self.db, projects_dir="/nonexistent")
        self.httpd = http.server.HTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}").read()

    def test_index_html(self):
        body = self._get("/")
        # New product is "מנהל הטוקנים" - check the unique brand id "DN" appears
        self.assertIn(b"DN", body)

    def test_overview_json(self):
        body = json.loads(self._get("/api/overview"))
        self.assertIn("sessions", body)
        self.assertEqual(body["sessions"], 1)

    def test_prompts_json(self):
        body = json.loads(self._get("/api/prompts?limit=10"))
        self.assertIsInstance(body, list)

    def test_projects_json(self):
        body = json.loads(self._get("/api/projects"))
        self.assertIsInstance(body, list)
        self.assertEqual(body[0]["project_slug"], "p")

    def test_plan_json(self):
        body = json.loads(self._get("/api/plan"))
        self.assertIn("plan", body)
        self.assertIn("pricing", body)

    def test_head_returns_200_not_501(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", method="HEAD")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read(), b"")

    def test_head_api_endpoint(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/overview", method="HEAD")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read(), b"")

    def test_foreign_host_header_rejected(self):
        # A page on the open web can point a hostname it controls at 127.0.0.1
        # and read this server through the browser. Pinning Host to loopback
        # closes that without affecting local use.
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/overview")
        req.add_header("Host", "evil.example.com")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 403)

    def test_static_path_traversal_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/web/../pricing.json")
        self.assertEqual(ctx.exception.code, 404)

    def test_prompts_respects_date_range(self):
        # The seeded prompt is dated 2026-04-19.
        inside = json.loads(self._get("/api/prompts?since=2026-04-01&until=2026-05-01"))
        outside = json.loads(self._get("/api/prompts?since=2026-01-01&until=2026-02-01"))
        self.assertEqual(len(inside), 1)
        self.assertEqual(outside, [])


class StreamFanoutTests(unittest.TestCase):
    """Every open dashboard tab must receive every event.

    The stream used to read from one shared queue, and queue.get() pops, so a
    second tab silently stopped refreshing.
    """

    def test_publish_reaches_every_subscriber(self):
        from token_dashboard import server

        a = server._subscribe()
        b = server._subscribe()
        try:
            server.publish({"type": "scan", "n": 1})
            self.assertEqual(a.get_nowait()["n"], 1)
            self.assertEqual(b.get_nowait()["n"], 1)
        finally:
            server._unsubscribe(a)
            server._unsubscribe(b)

    def test_slow_subscriber_does_not_grow_without_bound(self):
        from token_dashboard import server

        q = server._subscribe()
        try:
            for i in range(server.SUBSCRIBER_BACKLOG * 3):
                server.publish({"type": "scan", "n": i})
            self.assertLessEqual(q.qsize(), server.SUBSCRIBER_BACKLOG)
        finally:
            server._unsubscribe(q)

    def test_unsubscribe_stops_delivery(self):
        from token_dashboard import server

        q = server._subscribe()
        server._unsubscribe(q)
        server.publish({"type": "scan", "n": 7})
        self.assertTrue(q.empty())


if __name__ == "__main__":
    unittest.main()
