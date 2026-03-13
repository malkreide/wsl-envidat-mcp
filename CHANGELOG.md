# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
