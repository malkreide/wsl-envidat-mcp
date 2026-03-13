# wsl-envidat-mcp 🌲❄️⛰️

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Tests](https://img.shields.io/badge/tests-11%2F11-brightgreen)
![No API Key](https://img.shields.io/badge/API%20key-not%20required-green)

> MCP server for environmental research and monitoring data from the Swiss Federal Research Institute WSL via EnviDat — no API key required

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

The **WSL** (Eidgenössische Forschungsanstalt für Wald, Schnee und Landschaft / Swiss Federal Research Institute for Forest, Snow and Landscape) is one of Europe's leading environmental research institutes. Its open data platform **[EnviDat](https://www.envidat.ch)** provides access to 1,000+ research datasets, time series of up to 130 years, and data from 6,000+ monitoring stations.

This MCP server exposes the EnviDat CKAN API as 12 tools and 2 resources, enabling AI assistants to search, filter and retrieve WSL research data by keyword, domain, or geographic bounding box — all without an API key.

Part of the [Swiss Open Data MCP Portfolio](https://github.com/malkreide).

## Features

- **12 tools** covering full-text search, domain-specific queries, spatial search, and curated thematic tools (avalanche, forest, natural hazards)
- **2 MCP resources** for organizations and research domains
- **5 research domains**: Forest · Biodiversity · Natural Hazards · Snow & Ice · Landscape
- **815+ datasets**, time series since 1890, data from the SLF avalanche research institute
- **No API key required** — all data publicly accessible via open licenses
- **Dual transport**: stdio (Claude Desktop / local) + Streamable HTTP (cloud deployment)
- **Model-agnostic**: works with Claude, GPT-4, and any MCP-compatible client

## Prerequisites

- Python 3.11+
- `pip` or `uv` / `uvx`
- Internet connection (live API calls to envidat.ch)

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

## Usage / Quickstart

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

### Cloud Deployment (Streamable HTTP)

```bash
MCP_TRANSPORT=streamable_http PORT=8000 python -m wsl_envidat_mcp.server
```

## Configuration

No API key required. Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `streamable_http` |
| `PORT` | `8000` | Port for Streamable HTTP mode |

## Tools

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

## Resources

| URI | Description |
|-----|-------------|
| `envidat://organization/{name}` | Research unit (e.g. `slf`, `wsl`) |
| `envidat://domain/{domain}` | Domain overview with top datasets |

Valid domain values: `wald`, `biodiversitaet`, `naturgefahren`, `schnee_eis`, `landschaft`

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
├── README.md               # This file (English)
├── README.de.md            # German version
├── CHANGELOG.md
├── LICENSE                 # MIT
└── claude_desktop_config.json
```

## Combination with Other MCP Servers

This server is part of the Swiss Open Data MCP Portfolio and integrates well with:

| Combination | Use Case |
|-------------|----------|
| + `zurich-opendata-mcp` | Urban climate + forest condition around Zurich |
| + `swiss-statistics-mcp` | Population data + environmental quality |
| + `swiss-transport-mcp` | Avalanche risk + public transport connections |
| + `fedlex-mcp` | Forest protection law + actual LFI forest condition |
| + `global-education-mcp` | Compare environmental education data internationally |

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## License

MIT License — see [LICENSE](LICENSE)

Data on EnviDat is published under various open licenses (Creative Commons, CC0) — see individual dataset metadata.

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)  
Head of Marketing & Communication, Schulamt der Stadt Zürich  
Member, KI-Fachgruppe Stadtverwaltung Zürich
