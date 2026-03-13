# wsl-envidat-mcp 🌲❄️⛰️

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Tests](https://img.shields.io/badge/Tests-11%2F11-brightgreen)
![Kein API-Key](https://img.shields.io/badge/API--Key-nicht%20erforderlich-green)

> MCP-Server für Umweltforschungs- und Monitoringdaten der WSL via EnviDat — kein API-Schlüssel erforderlich

[🇬🇧 English Version](README.md)

---

## Übersicht

Die **WSL** (Eidgenössische Forschungsanstalt für Wald, Schnee und Landschaft) ist eine der führenden Umweltforschungsanstalten Europas. Ihre Offene-Daten-Plattform **[EnviDat](https://www.envidat.ch)** bietet Zugang zu 1'000+ Forschungsdatensätzen, Zeitreihen von bis zu 130 Jahren und Daten von 6'000+ Monitoring-Stationen.

Dieser MCP-Server stellt die EnviDat CKAN API als 12 Tools und 2 Resources bereit und ermöglicht KI-Assistenten die Suche und den Abruf von WSL-Forschungsdaten nach Stichwort, Domäne oder geografischem Begrenzungsrahmen — ohne API-Schlüssel.

Teil des [Swiss Open Data MCP-Portfolios](https://github.com/malkreide).

## Funktionen

- **12 Tools** für Volltextsuche, domänenspezifische Abfragen, räumliche Suche und kuratierte Thementools (Lawinen, Wald, Naturgefahren)
- **2 MCP Resources** für Organisationen und Forschungsdomänen
- **5 Forschungsdomänen**: Wald · Biodiversität · Naturgefahren · Schnee & Eis · Landschaft
- **815+ Datensätze**, Zeitreihen seit 1890, Daten des SLF-Lawinenforschungsinstituts
- **Kein API-Schlüssel** — alle Daten öffentlich zugänglich unter offenen Lizenzen
- **Dualer Transport**: stdio (Claude Desktop / lokal) + Streamable HTTP (Cloud-Deployment)
- **Modell-agnostisch**: funktioniert mit Claude, GPT-4 und jedem MCP-kompatiblen Client

## Voraussetzungen

- Python 3.11+
- `pip` oder `uv` / `uvx`
- Internetverbindung (Live-API-Abfragen an envidat.ch)

## Installation

```bash
# Empfohlen: uvx (keine Installation nötig)
uvx wsl-envidat-mcp

# Oder mit pip
pip install wsl-envidat-mcp

# Entwicklung
git clone https://github.com/malkreide/wsl-envidat-mcp.git
cd wsl-envidat-mcp
pip install -e ".[dev]"
```

## Verwendung / Quickstart

### Claude Desktop

Datei bearbeiten: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) oder `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

Claude Desktop neu starten, dann direkt fragen:

- *«Welche WSL-Datensätze gibt es zu tödlichen Lawinenunfällen in der Schweiz?»*
- *«Zeig mir Walddaten vom LFI für den Kanton Zürich.»*
- *«Welche Naturgefahren-Forschungsdaten publiziert das SLF auf EnviDat?»*
- *«Gibt es WSL-Daten zur Trockenheitssituation im Sommer 2022?»*
- *«Welche Biodiversitätsdaten gibt es für alpine Ökosysteme?»*

### Cloud-Deployment (Streamable HTTP)

```bash
MCP_TRANSPORT=streamable_http PORT=8000 python -m wsl_envidat_mcp.server
```

## Konfiguration

Kein API-Schlüssel erforderlich. Optionale Umgebungsvariablen:

| Variable | Standard | Beschreibung |
|----------|---------|--------------|
| `MCP_TRANSPORT` | `stdio` | Transportmodus: `stdio` oder `streamable_http` |
| `PORT` | `8000` | Port für Streamable-HTTP-Modus |

## Tools

| Tool | Beschreibung |
|------|-------------|
| `wsl_search_datasets` | Volltextsuche über alle Datensätze (Solr-Syntax möglich) |
| `wsl_get_dataset` | Vollständige Metadaten, DOI, Download-URLs |
| `wsl_search_by_domain` | Thematische Suche nach WSL-Forschungsdomäne |
| `wsl_search_by_location` | Räumliche Suche via Bounding Box |
| `wsl_list_organizations` | WSL-Forschungseinheiten auflisten |
| `wsl_get_organization` | Details einer Forschungseinheit inkl. Datensätze |
| `wsl_list_tags` | Schlagwörter durchsuchen |
| `wsl_get_recent_datasets` | Zuletzt aktualisierte Datensätze |
| `wsl_get_avalanche_data` | SLF Lawinen- & Schneedaten (inkl. tödliche Unfälle seit 1936) |
| `wsl_get_forest_data` | Walddaten inkl. LFI und Sanasilva |
| `wsl_get_naturgefahren_data` | Naturgefahren-Datensätze (Rutschungen, Steinschlag, Hochwasser) |
| `wsl_catalog_stats` | Katalog-Übersicht und Statistiken |

## Projektstruktur

```
wsl-envidat-mcp/
├── src/wsl_envidat_mcp/
│   ├── __init__.py         # Package
│   ├── server.py           # MCP-Server — 12 Tools, 2 Resources
│   └── api_client.py       # HTTP-Client für EnviDat CKAN API
├── tests/
│   └── test_integration.py # 11 Live-API-Integrationstests
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI (Python 3.11–3.13)
├── pyproject.toml          # Projektkonfiguration (hatchling)
├── README.md               # Englische Version
├── README.de.md            # Diese Datei
├── CHANGELOG.md
├── LICENSE                 # MIT
└── claude_desktop_config.json
```

## Kombination mit anderen MCP-Servern

Dieser Server ist Teil des Swiss Open Data MCP-Portfolios und lässt sich kombinieren mit:

| Kombination | Anwendungsfall |
|-------------|---------------|
| + `zurich-opendata-mcp` | Stadtklima + Waldzustand Zürich |
| + `swiss-statistics-mcp` | Bevölkerungsdaten + Umweltqualität |
| + `swiss-transport-mcp` | Lawinengefahr + ÖV-Verbindungen |
| + `fedlex-mcp` | Waldschutzrecht + Ist-Zustand LFI |
| + `global-education-mcp` | Umweltbildungsdaten international vergleichen |

## Tests

```bash
# Integrationstests (Live-API)
PYTHONPATH=src python tests/test_integration.py

# Linting
ruff check src/
```

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

Daten auf EnviDat werden unter verschiedenen offenen Lizenzen publiziert (Creative Commons, CC0) — siehe Metadaten der einzelnen Datensätze.

## Autorin

Hayal Oezkan · [malkreide](https://github.com/malkreide)  
Leiterin Marketing & Kommunikation, Schulamt der Stadt Zürich  
Mitglied KI-Fachgruppe Stadtverwaltung Zürich
