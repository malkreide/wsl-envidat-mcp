# v0.2.0 — Audit-driven hardening release

**mcp-audit-skill v1.0.0 run [2026-05-28](../audits/2026-05-28T061441-Z-wsl-envidat-mcp/audit-report.md): 31/32 checks pass, `production_ready: true`, 0 blocking findings.**

## ⚠️ Breaking changes

The three search tools have been unified into a single `wsl_search`:

```python
# Before (0.1.0)
wsl_search_datasets(query="snow avalanche")
wsl_search_by_domain(domain="wald")
wsl_search_by_location(min_lon=8.35, min_lat=47.15, max_lon=8.98, max_lat=47.72)

# After (0.2.0)
wsl_search(query="snow avalanche")
wsl_search(domain="wald")
wsl_search(bbox=[8.35, 47.15, 8.98, 47.72])

# New: combine filters in one call
wsl_search(query="bark beetle", organization="wsl", bbox=[8.35, 47.15, 8.98, 47.72])
```

Total tool surface drops from 12 to 10. The corresponding Pydantic input
classes (`SearchDatasetsInput`/`SearchByDomainInput`/`SearchByLocationInput`)
are replaced by a single `SearchInput`.

## Security hardening

- **SEC-007 — Container image** at `ghcr.io/malkreide/wsl-envidat-mcp` (multi-arch amd64+arm64, non-root uid=1000, multi-stage build)
- **SEC-005 / SEC-021 — Egress allow-list** + `follow_redirects=False` blocks cross-origin redirect hijack
- **SEC-016 — Explicit `MCP_HOST=127.0.0.1`** default for streamable-http; only `0.0.0.0` in container deployments
- **SEC-009 — Multi-tenant warning** for unauthenticated streamable-http; SDK pin `mcp>=1.3.0,<2.0.0`

## Observability & error handling

- **OBS-001 — ToolError-based errors:** Tools now raise `ToolError` instead of returning a plain-string error. FastMCP propagates this as `CallToolResult.isError=True` so clients can distinguish success from failure.
- **OBS-003 — structlog JSON logging** to stderr (RFC 5424 severities, ISO-8601 UTC timestamps).

## Architecture & docs

- **ARCH-002 — `<use_case>` / `<important_notes>` / `<example>` tags** in tool descriptions
- **ARCH-003 — Empty-result tag suggestions** via tag-prefix heuristic
- **ARCH-006 — Tool consolidation** (see Breaking changes above)
- **ARCH-012 — `SUPPORTED_MCP_PROTOCOL_VERSION`** constant with startup-time drift warning
- **CH-004 — OGD-CH attribution fields** (`source` / `license` / `provenance` / `retrieved_at`) in every JSON search response
- **OPS-002 / OPS-003 — Phase 1 declaration** in both READMEs

## Tests & CI

- **OPS-001 — Offline unit-test suite** (40 tests via respx, mocks all CKAN calls)
- **CI separation:** default job runs `pytest -m "not live"` (no network); live tests gated to `main` pushes and `workflow_dispatch`

## Fixed

- **Latent crash in `streamable-http` path:** the old `main()` called `mcp.run(transport="streamable_http", port=port)` which would have raised `TypeError` (no `port=` kwarg on `FastMCP.run`) and used a non-SDK transport string. The cloud-deployment path was broken on `main` before this release.

## Audit trail

Full re-audit results under `audits/2026-05-28T061441-Z-wsl-envidat-mcp/`:
- `summary.json` — single source of truth (`production_ready: true`, `blocking_findings: []`)
- `audit-report.md` — full report
- `findings/ARCH-002.md` — only remaining (medium, non-blocking)

Baseline comparison: `audits/2026-05-27T120439-Z-wsl-envidat-mcp/` (3 fails + 13 partials → 0 fails + 1 partial after this release).

## Container image

```bash
docker run --rm -p 8000:8000 \
  --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt=no-new-privileges \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  ghcr.io/malkreide/wsl-envidat-mcp:v0.2.0
```

## Install

```bash
uvx wsl-envidat-mcp           # auto-pulls latest from PyPI
pip install wsl-envidat-mcp==0.2.0
```

---

**Full changelog**: [v0.1.0…v0.2.0](https://github.com/malkreide/wsl-envidat-mcp/compare/v0.1.0...v0.2.0)
