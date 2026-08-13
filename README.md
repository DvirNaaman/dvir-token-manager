# Token Manager | DN

A local dashboard for analyzing Claude Code token usage. It reads the JSONL transcripts Claude Code stores under `~/.claude/projects/` and turns them into cost views, conversation history, top-spend prompt analysis, tool-usage heatmaps, cache analytics, cross-project comparisons, and skill usage breakdowns.

![Overview - KPIs, estimated cost, cache writes and reads](docs/images/dashboard-overview.png)

![Skills - top skills by invocations](docs/images/dashboard-skills.png)

## Fully private

The tool runs entirely on your machine. No telemetry, no outbound network calls, no third-party requests. The server listens on `127.0.0.1:8080` only. All assets (ECharts, Heebo, icons) are served locally from the `web/` directory.

For independent verification, see `PRIVACY_AUDIT.md` in the project directory.

## Requirements

- Python 3.8 or newer
- Claude Code installed with at least one existing conversation under `~/.claude/projects/`
- A modern browser (Chrome, Edge, Firefox)
- No `pip install` required. The tool uses the Python standard library only.

## Running

```bash
git clone https://github.com/DvirNaaman/dvir-token-manager.git
cd dvir-token-manager
python cli.py dashboard
```

The command starts the server at `http://127.0.0.1:8080` and opens it automatically in your browser. The server re-scans every 30 seconds and pushes live updates over SSE, so you don't need to refresh manually.

To stop: `Ctrl+C`.

## Additional CLI commands

```bash
python cli.py scan      # manually scan for new JSONL files
python cli.py today     # today's summary in the terminal
python cli.py stats     # all-time summary in the terminal
python cli.py tips      # savings tips based on usage patterns
```

Any command accepts `--db PATH` and `--projects-dir PATH` to override defaults.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `127.0.0.1` | Server listen address |
| `PORT` | `8080` | Server listen port |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Source of JSONL files |
| `TOKEN_DASHBOARD_DB` | `~/.claude/token-dashboard.db` | Location of the local SQLite database |

## Privacy blur shortcut

Pressing `Ctrl + B` anywhere in the dashboard blurs prompt text and sensitive content, useful for screenshots. Press again to unblur.

## How to verify zero outbound calls

macOS / Linux:

```bash
grep -rEi "https?://(?!127\.0\.0\.1|localhost)" --include="*.py" --include="*.js" --include="*.html" --include="*.css" .
```

Windows (PowerShell):

```powershell
Get-ChildItem -Recurse -Include *.py,*.js,*.html,*.css |
  Select-String -Pattern 'https?://(?!127\.0\.0\.1|localhost)'
```

The output should be empty aside from comments in ECharts LICENSE headers and the upstream attribution links listed in `PRIVACY_AUDIT.md`.

## Credits and license

- **Original engine:** [Nate Herk](https://github.com/nateherkai) — author of the original JSONL analyzer and dashboard code, released under the MIT license.
- **Hebrew/RTL adaptation, UI, and branding:** [Dvir Naaman](https://github.com/DvirNaaman) — full UI rewrite, translation, Meridian palette, local Heebo font, tips engine, and iconography.

The project as a whole is distributed under the MIT license (see the `LICENSE` file). You're welcome to use, modify, and distribute it — just preserve both copyright lines in the license file.

## Troubleshooting

**Hebrew text shows as mojibake in the terminal on Windows:** run `chcp 65001` once in the CMD window before the command, or use PowerShell / Windows Terminal which support UTF-8 by default.

**Dashboard is empty:** make sure at least one conversation exists under `~/.claude/projects/<slug>/<session>.jsonl`. In non-standard environments, point to it manually with `--projects-dir`.

**Port in use:** run with a different port.

- macOS / Linux: `PORT=8090 python cli.py dashboard`
- Windows (PowerShell): `$env:PORT=8090; python cli.py dashboard`
- Windows (CMD): `set PORT=8090 && python cli.py dashboard`

## Refresh, 2026-08-13

The whole codebase went through a review, refresh and upgrade pass on this date. Nothing was removed and no tab changed shape; the corrections were to the numbers the dashboard reports and to how the server behaves.

**Costs are correct again.** `pricing.json` still held the previous generation of models at their old rates, so every Opus turn was priced at three times its real cost and nothing in the Claude 5 family resolved at all. The table now covers Claude Opus 5, Sonnet 5, Fable 5 and the 4.x line at current list rates, and model ids carrying a context-window suffix (`claude-opus-5[1m]`) or a dated snapshot suffix (`claude-haiku-4-5-20251001`) resolve to their base model instead of falling through to a coarse tier guess. The right-sizing tip reads its rates from that same file rather than from two numbers hardcoded in the tips engine, where they had silently gone stale.

**Multiple dashboard tabs work.** The event stream read from one shared queue, and reading from a queue removes the item, so with two tabs open each live update reached only one of them and the other quietly stopped refreshing. Every stream now has its own bounded queue.

**The server is harder to reach from outside.** Requests whose `Host` header is not a loopback name are rejected, which closes the DNS-rebinding path that let a page on the open web read this server through your browser. Static file serving no longer accepts a sibling directory whose name merely starts like the web root, and `HEAD` no longer writes a body.

**The date range applies everywhere.** The prompts tab accepted `since` and `until` and then ignored them, so it always showed all time while every other tab honoured the filter.

**Listings are faster.** The projects and conversations views ran one extra query per project to work out display names. That is now a single grouped read, and a missing index on `parent_uuid` was making the prompt-to-answer join a full table scan.

**Hebrew CLI output survives a pipe.** On a Hebrew Windows machine, anything reading the CLI's output through a pipe decoded it with the local codepage and failed on the Hebrew bytes, losing the output entirely.

The Hebrew label for the per-project turn count read "סשנים", which is the word already used for conversations one column over; it now reads "פניות". The test suite covers all of this and stands at 82 tests.

## A note on Claude Opus 4.8

This dashboard is built and maintained with Claude Code. When Claude Opus 4.8 was released we moved our development workflow over to it straight away and refreshed the project's tooling to match. In daily use we found 4.8 noticeably sharper at multi step reasoning and large context work than the earlier 4.x models, which made maintaining a token analytics tool like this one, with its careful data parsing and many edge cases, considerably smoother. As part of this refresh the model identifiers and defaults across our projects were updated to Opus 4.8.
