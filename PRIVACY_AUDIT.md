# Privacy Audit — Dvir Token Manager

Date: 2026-04-29
Method: static grep across the repo for outbound network indicators.

## Result: clean

Zero outbound calls. All network activity is bound to `127.0.0.1`.

## Commands run

```bash
grep -rEi "https?://" .
grep -rEi "fetch\(|XMLHttpRequest|requests\.|urllib|http\.client|httplib|websocket|socket\.|urlopen" .
grep -rEi "google-analytics|gtag|plausible|sentry|mixpanel|posthog|hotjar|datadog|amplitude" .
```

## Findings

| Indicator | Match count | Disposition |
|---|---|---|
| Analytics SDKs | 0 | none present |
| External `fetch()` calls in JS | 0 | all relative paths to `/api/*` |
| `urllib` / sockets in Python | tests + server.py | bound to `127.0.0.1` only |
| External HTTPS URLs | comments + readme + license headers + (1) reference to upstream inspiration in `docs/inspiration.md` and `CLAUDE.md` | not executed at runtime |
| Third-party CDN script tags | 0 | ECharts is vendored at `web/echarts.min.js`, no CDN load |
| Google Fonts / external font CDN | 0 | system fonts only (we are about to self-host Heebo locally to preserve this property) |

## Remaining external URLs (text only, never fetched)

- `https://github.com/phuryn/claude-usage` - attribution text in `docs/inspiration.md` (commentary only)
- `http://www.apache.org/licenses/LICENSE-2.0` - license header inside `web/echarts.min.js`
- `https://github.com/ecomfe/zrender/blob/master/LICENSE.txt` - license header inside `web/echarts.min.js`

None of these are loaded, fetched, or executed at runtime.

## Self-hosted assets verification

- ECharts: vendored at `web/echarts.min.js` (no CDN load)
- Heebo font: vendored at `web/assets/fonts/heebo-{hebrew,latin,latin-ext}.woff2` with local CSS at `web/assets/fonts/heebo.css` (no Google Fonts CDN load at runtime)
- DN brand logo + favicon: vendored at `web/assets/brand/`

## How to re-verify

Run the same three grep commands above from the repo root. If any match appears outside the "Remaining external URLs" list, investigate before launching the dashboard.
