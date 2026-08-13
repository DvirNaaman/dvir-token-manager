# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

**Dvir Token Manager** ("מנהל הטוקנים | DN") - a Hebrew/RTL local dashboard for tracking Claude Code token usage, costs, and session history. Reads the JSONL transcripts Claude Code writes to `~/.claude/projects/` and turns them into per-prompt cost analytics, tool/file heatmaps, subagent attribution, cache analytics, project comparisons, and a rule-based tips engine.

Adapted from a permissively-licensed upstream codebase. The UI, language, and brand are fully owned by Dvir Naaman; the underlying engine is MIT (see `LICENSE`).

## Status

Working codebase. 82 Python unit tests (`python -m unittest discover tests`). Seven UI tabs wired up: סקירה כללית, פרומפטים, שיחות, פרויקטים, מיומנויות, טיפים לחיסכון, הגדרות. Runs on Windows, macOS, and Linux.

Last full review and refresh pass: **2026-08-13**. See the "Refresh, 2026-08-13" section of `README.md` for what changed and why.

## Invariants worth knowing before editing

- **`pricing.json` is the only place rates live.** Do not hardcode a per-token price anywhere else; `tips.py` used to, and the numbers went stale without anything failing. Model ids go through `pricing.normalize_model` first, which strips a `[1m]`-style context suffix and a `-YYYYMMDD` snapshot suffix so both price as the base model.
- **The SSE stream fans out.** `server.publish()` writes to one bounded queue per connected client. Do not go back to a single shared queue: `queue.get()` pops, so one shared queue starves every tab but one, silently.
- **`turns` counts user messages, not sessions.** The Hebrew label is "פניות"; "שיחות" is reserved for `sessions`.
- **The CLI writes UTF-8 deliberately.** Anything reading its output through a pipe must decode UTF-8 explicitly, or a Hebrew Windows locale decodes with cp1255 and the output is lost.

## Architecture

- `cli.py` → `token_dashboard/scanner.py` → `~/.claude/token-dashboard.db` (SQLite)
- `token_dashboard/server.py` exposes JSON APIs (`/api/*`) + SSE stream (`/api/stream`) + static frontend (`web/`)
- `web/` is vanilla JS, no build step - hash router + ECharts (vendored at `web/echarts.min.js`)
- `web/assets/brand/` - DN logo and favicon
- `web/assets/fonts/` - self-hosted Heebo (hebrew + latin + latin-ext)

## Conventions

- **Fully local.** Zero outbound calls. ECharts vendored, Heebo self-hosted, no Google Fonts CDN at runtime, no analytics.
- **Stdlib only.** No `pip install`. If a feature truly needs a third-party library, raise it before adding.
- **RTL-first CSS.** Use logical properties (`margin-inline-start`, `border-block-end`, `text-align: start`) - not physical (`margin-left`, `border-bottom`, `text-align: left`).
- **Hebrew UI strings are inline in JS/HTML.** No i18n indirection - this is a single-language tool.
- **SQLite parameter binding always.** Any f-string in a SQL statement must interpolate only internal, caller-controlled values. User-reachable values go through `?`.
- **Brand tokens centralised** at the top of `web/style.css` (`:root` block). Re-use `var(--c-*)` rather than hardcoding hex.

## Customizing

Env vars: `PORT` (default 8080), `HOST` (default 127.0.0.1), `CLAUDE_PROJECTS_DIR`, `TOKEN_DASHBOARD_DB`. Pricing lives in `pricing.json`. See README.md.

## Verifying changes

```bash
python -m unittest discover tests          # all tests
python cli.py dashboard --no-open          # start the server
curl http://127.0.0.1:8080/api/overview    # sanity-check an endpoint
```

After any change: re-run the privacy grep documented in `PRIVACY_AUDIT.md` to confirm zero outbound URLs were introduced.
