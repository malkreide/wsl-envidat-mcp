# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-28

### Breaking changes

- **Tool consolidation (ARCH-006):** Replaced the three separate search
  tools `wsl_search_datasets`, `wsl_search_by_domain` and
  `wsl_search_by_location` with a single unified `wsl_search` tool that
  accepts optional `query`, `domain`, `organization` and `bbox` filters
  (at least one is required). Total tool surface drops from 12 to 10.

  **Migration**:

  ```python
  # Before (0.1.0)
  wsl_search_datasets(query="snow avalanche", limit=5)
  wsl_search_by_domain(domain="wald")
  wsl_search_by_location(min_lon=8.35, min_lat=47.15,
                         max_lon=8.98, max_lat=47.72)

  # After (0.2.0)
  wsl_search(query="snow avalanche", limit=5)
  wsl_search(domain="wald")
  wsl_search(bbox=[8.35, 47.15, 8.98, 47.72])

  # New: combine filters
  wsl_search(query="bark beetle", organization="wsl",
             bbox=[8.35, 47.15, 8.98, 47.72])
  ```

  The corresponding Pydantic input classes
  (`SearchDatasetsInput` / `SearchByDomainInput` / `SearchByLocationInput`)
  are replaced by a single `SearchInput`.

### Added (Audit-Run 2026-05-27, mcp-audit-skill v1.0.0)

- **Container image** at `ghcr.io/malkreide/wsl-envidat-mcp` (multi-arch,
  non-root uid 1000, distroless-style multi-stage build) — SEC-007
- **`wsl_search` unified search tool** with optional query/domain/
  organization/bbox filters — ARCH-006
- **Empty-result tag suggestions** via tag-prefix heuristic — ARCH-003
- **Structured `<use_case>` / `<important_notes>` / `<example>` tags** in
  tool descriptions (4 search-oriented tools) — ARCH-002
- **`MCP_HOST` env var** (default `127.0.0.1`) for streamable-http
  binding — SEC-016
- **Egress allow-list** (`ALLOWED_HOSTS = {www.envidat.ch, envidat.ch}`)
  with `assert_host_allowed()` and `follow_redirects=False` — SEC-021,
  SEC-005
- **structlog** as runtime dependency, JSON logs on stderr — OBS-003
- **`SUPPORTED_MCP_PROTOCOL_VERSION`** constant with startup-time drift
  warning against `mcp.types.LATEST_PROTOCOL_VERSION` — ARCH-012
- **OGD-CH attribution fields** (`source` / `license` / `provenance` /
  `retrieved_at`) in every JSON search response — CH-004
- **Phase section** in both READMEs declaring Phase 1 (Read-only Wrapper)
  with audit-run status — OPS-002, OPS-003
- **Offline unit-test suite** with respx-mocked tests for all tools —
  OPS-001
- **CI separation**: default job runs `pytest -m "not live"` (no
  network); live tests run only on `main` pushes and
  `workflow_dispatch` — OPS-001
- Multi-tenant warning in cloud-deployment sections — SEC-009
- Audit findings under `audits/2026-05-27T120439-Z-wsl-envidat-mcp/`

### Changed

- **Error handling (OBS-001):** Tool failures now raise `ToolError`
  instead of returning a plain error string. FastMCP propagates this as
  `CallToolResult.isError=True`, so MCP clients can finally distinguish
  success from failure.
- **`MCP_TRANSPORT`** value: canonical form is now `streamable-http`
  (hyphen); the legacy `streamable_http` is still accepted for
  backwards compatibility.
- **`pyproject.toml`**: `mcp>=1.3.0,<2.0.0` upper-bound; `structlog`,
  `respx` added.

### Fixed

- **Latent crash in `streamable-http` path:** the old `main()` called
  `mcp.run(transport="streamable_http", port=port)` which raised
  `TypeError` (no `port=` kwarg on `FastMCP.run`) and used a non-SDK
  transport string. The cloud-deployment path was broken on `main`
  before this release.

## [0.1.0] - 2026-03-13

### Added
- 12 tools for EnviDat CKAN API access
  - `wsl_search_datasets` — Full-text search across 1,000+ datasets
  - `wsl_get_dataset` — Full metadata incl. DOI and download URLs
  - `wsl_search_by_domain` — Thematic search (5 WSL research domains)
  - `wsl_search_by_location` — Spatial search via bounding box
  - `wsl_list_organizations` — List WSL research units
  - `wsl_get_organization` — Research unit details
  - `wsl_list_tags` — Browse tags/keywords
  - `wsl_get_recent_datasets` — Most recently updated datasets
  - `wsl_get_avalanche_data` — SLF avalanche & snow data
  - `wsl_get_forest_data` — Forest data incl. LFI and Sanasilva
  - `wsl_get_naturgefahren_data` — Natural hazard datasets
  - `wsl_catalog_stats` — Catalog overview and statistics
- 2 MCP resources
  - `envidat://organization/{name}` — Organization as resource
  - `envidat://domain/{domain}` — Domain overview as resource
- Dual transport: stdio (Claude Desktop) + Streamable HTTP (cloud)
- Bilingual documentation: English primary (README.md) + German (README.de.md)
- 11 live API integration tests (11/11 passing)
- GitHub Actions CI (Python 3.11–3.13)
