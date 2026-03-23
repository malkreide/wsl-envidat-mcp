[🇬🇧 English Version](README.md)

> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# wsl-envidat-mcp 🌲❄️⛰️

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Datenquelle](https://img.shields.io/badge/Daten-envidat.ch-green)](https://www.envidat.ch/)
[![Kein API-Key](https://img.shields.io/badge/API--Key-nicht%20erforderlich-brightgreen)](https://www.envidat.ch/)
![CI](https://github.com/malkreide/wsl-envidat-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server, der KI-Modelle mit Schweizer Umweltforschungsdaten der WSL via EnviDat verbindet — Wald, Schnee, Lawinen, Naturgefahren und Biodiversität, kein API-Schlüssel erforderlich.

---

## Übersicht

Die **WSL** (Eidgenössische Forschungsanstalt für Wald, Schnee und Landschaft) ist eine der führenden Umweltforschungsanstalten Europas. Ihre Offene-Daten-Plattform **[EnviDat](https://www.envidat.ch)** bietet Zugang zu 1'000+ Forschungsdatensätzen, Zeitreihen von bis zu 130 Jahren und Daten von 6'000+ Monitoring-Stationen.

Dieser MCP-Server stellt die EnviDat CKAN API als 12 Tools und 2 Resources bereit und ermöglicht KI-Assistenten die Suche und den Abruf von WSL-Forschungsdaten nach Stichwort, Domäne oder geografischem Begrenzungsrahmen — ohne API-Schlüssel.

**Anker-Demo-Abfrage:** *«Wie war die Luftqualität und der Waldzustand rund um das Schulhaus Leutschenbach in Zürich — und was sagt die WSL zum aktuellen Waldzustand im Kanton?»*

---

## Funktionen

- **12 Tools** für Volltextsuche, domänenspezifische Abfragen, räumliche Suche und kuratierte Thementools (Lawinen, Wald, Naturgefahren)
- **2 MCP Resources** für Organisationen und Forschungsdomänen
- **5 Forschungsdomänen**: Wald · Biodiversität · Naturgefahren · Schnee & Eis · Landschaft
- **815+ Datensätze**, Zeitreihen seit 1890, Daten des SLF-Lawinenforschungsinstituts
- **Kein API-Schlüssel** — alle Daten öffentlich zugänglich unter offenen Lizenzen
- **Dualer Transport**: stdio (Claude Desktop / lokal) + Streamable HTTP (Cloud-Deployment)
- **Modell-agnostisch**: funktioniert mit Claude, GPT-4 und jedem MCP-kompatiblen Client

---

## Voraussetzungen

- Python 3.11+
- `pip` oder `uv` / `uvx`
- Internetverbindung (Live-API-Abfragen an envidat.ch)

---

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

---

## Schnellstart

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

---

## Konfiguration

Kein API-Schlüssel erforderlich. Optionale Umgebungsvariablen:

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `MCP_TRANSPORT` | `stdio` | Transportmodus: `stdio` oder `streamable_http` |
| `PORT` | `8000` | Port für Streamable-HTTP-Modus |

### Cloud-Deployment (Streamable HTTP)

Für den Einsatz via **claude.ai im Browser** (z.B. auf verwalteten Arbeitsplätzen ohne lokale Software):

```bash
MCP_TRANSPORT=streamable_http PORT=8000 python -m wsl_envidat_mcp.server
```

> 💡 *«stdio für den Entwickler-Laptop, SSE für den Browser.»*

---

## Verfügbare Tools

| Tool | Beschreibung |
|------|--------------|
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

### Beispiel-Abfragen

| Abfrage | Tool |
|---------|------|
| *«Tödliche Lawinenunfälle im Wallis seit 2000?»* | `wsl_get_avalanche_data` |
| *«Waldzustandsdaten für den Kanton Zürich?»* | `wsl_get_forest_data` |
| *«Datensätze zu Rutschungen in der Nähe von Brienz?»* | `wsl_get_naturgefahren_data` |
| *«Neueste WSL-Publikationen zur Biodiversität?»* | `wsl_search_by_domain` |
| *«Welche Datensätze gibt es rund um den Bodensee?»* | `wsl_search_by_location` |
| *«Wie viele Datensätze publiziert das SLF?»* | `wsl_get_organization` |

---

## Resources

| URI | Beschreibung |
|-----|--------------|
| `envidat://organization/{name}` | Forschungseinheit (z.B. `slf`, `wsl`) |
| `envidat://domain/{domain}` | Domänen-Übersicht mit Top-Datensätzen |

Gültige Domain-Werte: `wald`, `biodiversitaet`, `naturgefahren`, `schnee_eis`, `landschaft`

---

## Architektur

```
┌─────────────────┐     ┌───────────────────────────┐     ┌──────────────────────────┐
│   Claude / KI   │────▶│    WSL EnviDat MCP        │────▶│       envidat.ch          │
│   (MCP Host)    │◀────│    (MCP Server)           │◀────│                          │
└─────────────────┘     │                           │     │  CKAN API  (REST/JSON)   │
                        │  12 Tools · 2 Resources   │     │  Solr-Volltextsuche      │
                        │  Stdio | Streamable HTTP  │     │  1'000+ Forschungsdaten  │
                        │                           │     │  815+ offene Datensätze  │
                        │  server.py                │     │  Zeitreihen seit 1890    │
                        │  api_client.py            │     └──────────────────────────┘
                        └───────────────────────────┘
```

### Infrastruktur-Komponenten

| Komponente | Metapher | Funktion |
|------------|----------|----------|
| `api_client.py` | Bibliothekar | Alle HTTP-Anfragen an die EnviDat CKAN API |
| `server.py` | Empfangstheke | Registriert alle 12 Tools und 2 Resources bei FastMCP |
| Domain-Filter | Karteikasten | Vorkonfigurierte Schlüsselwort-Sets pro Forschungsdomäne |
| Bounding-Box-Suche | Kartenoverlay | Räumliche Filterung via Lat/Lon-Koordinaten |

---

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
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                 # MIT
├── README.md               # Englische Version
└── README.de.md            # Diese Datei
```

---

## Kombination mit anderen MCP-Servern

Dieser Server ist Teil des Swiss Open Data MCP-Portfolios und lässt sich kombinieren mit:

| Kombination | Anwendungsfall |
|-------------|----------------|
| + `zurich-opendata-mcp` | Stadtklima + Waldzustand Zürich |
| + `swiss-statistics-mcp` | Bevölkerungsdaten + Umweltqualität |
| + `swiss-transport-mcp` | Lawinengefahr + ÖV-Verbindungen |
| + `fedlex-mcp` | Waldschutzrecht + Ist-Zustand LFI |
| + `global-education-mcp` | Umweltbildungsdaten international vergleichen |

---

## Bekannte Einschränkungen

- **Solr-Suche**: `OR` wird als Stopwort behandelt — pro Abfrage nur einzelne, spezifische Suchbegriffe verwenden
- **Domänen-Suche**: Ergebnisse hängen von der internen Verschlagwortung durch WSL ab — nicht alle Datensätze sind konsistent getaggt
- **Räumliche Suche**: Bounding-Box-Filterung ist näherungsweise; Koordinaten anhand der Datensatz-Metadaten verifizieren
- **Live-API**: Alle Tools rufen envidat.ch live ab — Ergebnisse hängen von der Verfügbarkeit der öffentlichen API ab
- **Sprachen**: Datensatz-Metadaten primär auf Englisch und Deutsch; ältere Einträge teilweise nur auf Deutsch

---

## Tests

```bash
# Unit-Tests (kein API-Schlüssel, kein Netzwerkzugriff)
PYTHONPATH=src pytest tests/ -m "not live"

# Integrationstests (Live-API-Abfragen an envidat.ch)
PYTHONPATH=src pytest tests/ -m "live"

# Linting
ruff check src/
```

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Mitwirken

Siehe [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

Daten auf EnviDat werden unter verschiedenen offenen Lizenzen publiziert (Creative Commons, CC0) — siehe Metadaten der einzelnen Datensätze.

---

## Autorin

Hayal Oezkan · [malkreide](https://github.com/malkreide)  

---

## Credits & Verwandte Projekte

- **Daten:** [EnviDat](https://www.envidat.ch/) – WSL Eidgenössische Forschungsanstalt für Wald, Schnee und Landschaft
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)
