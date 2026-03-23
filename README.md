> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# wsl-envidat-mcp 🌲❄️⛰️

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Data Source](https://img.shields.io/badge/Data-envidat.ch-green)](https://www.envidat.ch/)
[![No API Key](https://img.shields.io/badge/API%20key-not%20required-brightgreen)](https://www.envidat.ch/)
![CI](https://github.com/malkreide/wsl-envidat-mcp/actions/workflows/ci.yml/badge.svg)

> MCP server connecting AI models to Swiss environmental research data from WSL via EnviDat — forest, snow, avalanches, natural hazards and biodiversity, no API key required.

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

The **WSL** (Eidgenössische Forschungsanstalt für Wald, Schnee und Landschaft / Swiss Federal Research Institute for Forest, Snow and Landscape) is one of Europe's leading environmental research institutes. Its open data platform **[EnviDat](https://www.envidat.ch)** provides access to 1,000+ research datasets, time series of up to 130 years, and data from 6,000+ monitoring stations.

This MCP server exposes the EnviDat CKAN API as 12 tools and 2 resources, enabling AI assistants to search, filter and retrieve WSL research data by keyword, domain, or geographic bounding box — all without an API key.

**Anchor demo query:** *"How was air quality and forest health around Schulhaus Leutschenbach in Zurich — and what does the WSL say about the current forest condition in the canton?"*

---

## Features

- **12 tools** covering full-text search, domain-specific queries, spatial search, and curated thematic tools (avalanche, forest, natural hazards)
- **2 MCP resources** for organizations and research domains
- **5 research domains**: Forest · Biodiversity · Natural Hazards · Snow & Ice · Landscape
- **815+ datasets**, time series since 1890, data from the SLF avalanche research institute
- **No API key required** — all data publicly accessible via open licenses
- **Dual transport**: stdio (Claude Desktop / local) + Streamable HTTP (cloud deployment)
- **Model-agnostic**: works with Claude, GPT-4, and any MCP-compatible client

---

## Prerequisites

- Python 3.11+
- `pip` or `uv` / `uvx`
- Internet connection (live API calls to envidat.ch)

---

## Installation

```bash
# Recommended: uvx (no installation needed)
uvx wsl-envidat-mcp

# Or with pip
pip install wsl-envidat-mcp

# Development
git clone https://github.com/malkreide/wsl-envidat-mcp.git
cd wsl-envidat-mcp
pip install -e ".[dev]"
```

---

## Quickstart

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "wsl-envidat": {
      "command": "uvx",
      "args": ["wsl-envidat-mcp"]
    }
  }
}
```

Restart Claude Desktop, then ask:

- *"What WSL datasets exist on fatal avalanche accidents in Switzerland?"*
- *"Show me forest inventory data from the LFI for the canton of Zurich."*
- *"Which natural hazard research data does the SLF publish on EnviDat?"*
- *"Are there WSL datasets on drought conditions in summer 2022?"*
- *"What biodiversity data is available for alpine ecosystems?"*

---

## Configuration

No API key required. Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `streamable_http` |
| `PORT` | `8000` | Port for Streamable HTTP mode |

### Cloud Deployment (Streamable HTTP)

For use via **claude.ai in the browser** (e.g. on managed workstations without local software):

```bash
MCP_TRANSPORT=streamable_http PORT=8000 python -m wsl_envidat_mcp.server
```

> 💡 *"stdio for the developer laptop, SSE for the browser."*

---

## Available Tools

| Tool | Description |
|------|-------------|
| `wsl_search_datasets` | Full-text search across all datasets (Solr syntax supported) |
| `wsl_get_dataset` | Full metadata, DOI, download URLs for a specific dataset |
| `wsl_search_by_domain` | Thematic search by WSL research domain |
| `wsl_search_by_location` | Spatial search via bounding box coordinates |
| `wsl_list_organizations` | List all WSL research units on EnviDat |
| `wsl_get_organization` | Details of a specific research unit incl. datasets |
| `wsl_list_tags` | Browse available tags/keywords |
| `wsl_get_recent_datasets` | Most recently updated datasets |
| `wsl_get_avalanche_data` | SLF avalanche & snow data (incl. fatal accidents since 1936) |
| `wsl_get_forest_data` | Forest data incl. National Forest Inventory (LFI) & Sanasilva |
| `wsl_get_naturgefahren_data` | Natural hazard datasets (landslides, rockfall, floods) |
| `wsl_catalog_stats` | Catalog overview and statistics |

### Example Use Cases

| Query | Tool |
|-------|------|
| *"Fatal avalanche accidents in Valais since 2000?"* | `wsl_get_avalanche_data` |
| *"Forest health data for canton Zurich?"* | `wsl_get_forest_data` |
| *"Landslide risk datasets near Brienz?"* | `wsl_get_naturgefahren_data` |
| *"Most recent WSL publications on biodiversity?"* | `wsl_search_by_domain` |
| *"Which datasets cover the area around Lake Constance?"* | `wsl_search_by_location` |
| *"How many datasets does SLF publish?"* | `wsl_get_organization` |

---

## Resources

| URI | Description |
|-----|-------------|
| `envidat://organization/{name}` | Research unit (e.g. `slf`, `wsl`) |
| `envidat://domain/{domain}` | Domain overview with top datasets |

Valid domain values: `wald`, `biodiversitaet`, `naturgefahren`, `schnee_eis`, `landschaft`

---

## Architecture

```
┌─────────────────┐     ┌───────────────────────────┐     ┌──────────────────────────┐
│   Claude / AI   │────▶│    WSL EnviDat MCP        │────▶│       envidat.ch          │
│   (MCP Host)    │◀────│    (MCP Server)           │◀────│                          │
└─────────────────┘     │                           │     │  CKAN API  (REST/JSON)   │
                        │  12 Tools · 2 Resources   │     │  Solr full-text search   │
                        │  Stdio | Streamable HTTP  │     │  1,000+ research datasets│
                        │                           │     │  815+ open datasets      │
                        │  server.py                │     │  Time series since 1890  │
                        │  api_client.py            │     └──────────────────────────┘
                        └───────────────────────────┘
```

### Infrastructure Components

| Component | Metaphor | Function |
|-----------|----------|----------|
| `api_client.py` | Librarian | Handles all HTTP requests to EnviDat CKAN API |
| `server.py` | Reception desk | Registers all 12 tools and 2 resources with FastMCP |
| Domain filters | Filing cabinet | Pre-configured keyword sets per research domain |
| Bounding box search | Map overlay | Spatial filtering via lat/lon coordinates |

---

## Project Structure

```
wsl-envidat-mcp/
├── src/wsl_envidat_mcp/
│   ├── __init__.py         # Package
│   ├── server.py           # MCP server — 12 tools, 2 resources
│   └── api_client.py       # HTTP client for EnviDat CKAN API
├── tests/
│   └── test_integration.py # 11 live API integration tests
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI (Python 3.11–3.13)
├── pyproject.toml          # Project config (hatchling build backend)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                 # MIT
├── README.md               # This file (English)
└── README.de.md            # German version
```

---

## Combination with Other MCP Servers

This server is part of the Swiss Open Data MCP Portfolio and integrates well with:

| Combination | Use Case |
|-------------|----------|
| + `zurich-opendata-mcp` | Urban climate + forest condition around Zurich |
| + `swiss-statistics-mcp` | Population data + environmental quality |
| + `swiss-transport-mcp` | Avalanche risk + public transport connections |
| + `fedlex-mcp` | Forest protection law + actual LFI forest condition |
| + `global-education-mcp` | Compare environmental education data internationally |

---

## Known Limitations

- **Solr search**: `OR` is treated as a stopword — use single, specific search terms per query
- **Domain search**: Results depend on WSL's internal keyword tagging — not all datasets are tagged consistently
- **Spatial search**: Bounding box filtering is approximate; verify coordinates with individual dataset metadata
- **Live API**: All tools make live calls to envidat.ch — results depend on availability of the public API
- **Languages**: Dataset metadata is primarily in English and German; some older entries may be in German only

---

## Testing

```bash
# Unit tests (no API key required, no network access)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live API calls to envidat.ch)
PYTHONPATH=src pytest tests/ -m "live"

# Linting
ruff check src/
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## License

MIT License — see [LICENSE](LICENSE)

Data on EnviDat is published under various open licenses (Creative Commons, CC0) — see individual dataset metadata.

---

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)  

---

## Credits & Related Projects

- **Data:** [EnviDat](https://www.envidat.ch/) – WSL Swiss Federal Research Institute for Forest, Snow and Landscape
- **Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)
