# MCP-Server Audit-Report — `wsl-envidat-mcp`

**Audit-Datum:** 
**Skill-Version:** 1.0.0
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `wsl-envidat-mcp` wurde gegen 32 anwendbare Best-Practice-Checks geprüft. 16 bestanden, 16 Findings dokumentiert (2 critical, 8 high, 6 medium, 0 low). Production-Readiness: NICHT erreicht — blockierend: OPS-001, SEC-007.

**Production-Readiness:** NO

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `wsl-envidat-mcp` |
| Audit-Datum | ? |
| Skill-Version | 1.0.0 |
| Catalog-Version | ? |
| transport | `dual` |
| auth_model | `none` |
| data_class | `Public Open Data` |
| write_capable | `False` |
| deployment | `['local-stdio']` |
| uses_sampling | `False` |
| tools_make_external_requests | `True` |
| stadt_zuerich_context | `False` |
| schulamt_context | `False` |
| data_source.is_swiss_open_data | `True` |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 7 | 0 | 4 | 0 | 0 |
| CH | 0 | 0 | 1 | 0 | 0 |
| OBS | 2 | 1 | 1 | 0 | 0 |
| OPS | 0 | 1 | 2 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SEC | 7 | 1 | 4 | 0 | 0 |
| **Total** | **16** | **3** | **13** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-009 | SEC | critical | partial |
| SEC-016 | SEC | critical | partial |
| ARCH-006 | ARCH | high | partial |
| OBS-001 | OBS | high | partial |
| OPS-001 | OPS | high | fail |
| OPS-003 | OPS | high | partial |
| SCALE-002 | SCALE | high | partial |
| SEC-005 | SEC | high | partial |
| SEC-007 | SEC | high | fail |
| SEC-021 | SEC | high | partial |
| ARCH-002 | ARCH | medium | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| CH-004 | CH | medium | partial |
| OBS-003 | OBS | medium | fail |
| OPS-002 | OPS | medium | partial |

**Gesamt:** 16 Findings

---

## 5. Detail-Findings

### ARCH-002

# Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `ARCH-002` |
| **PDF-Reference** | Sec 2.3 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Tool-Docstrings sind ausführlich und mehrsprachig (server.py:313, 361, 461, 516, ...). Pydantic-Field-Descriptions liefern Beispiele.

Aber: kein systematischer `<use_case>` / `<important_notes>` / `<example>`-Tag-Marker in den Tool-`description`-Strings — der LLM kann Kontext nicht maschinell aus dem Docstring extrahieren.

### Expected Behavior

```python
@mcp.tool(
    name="wsl_search_datasets",
    description=(
        "Durchsucht den EnviDat-Katalog der WSL nach Umweltforschungsdaten.\n\n"
        "<use_case>Klimafolgen-Recherche, Schulhaus-Umgebungsanalysen, "
        "kantonale Umweltberichte, Waldzustands-Reports.</use_case>\n\n"
        "<important_notes>Solr-Syntax möglich, aber 'OR' ist Stopwort — "
        "lieber einzelne präzise Begriffe verwenden.</important_notes>\n\n"
        "<example>query='snow avalanche' → SLF-Lawinenforschungs-Datasets</example>"
    ),
    annotations={...},
)
```

### Evidence

- `grep -rE '<use_case>|<important_notes>|<example>' src/`: 0 matches
- File: `src/wsl_envidat_mcp/server.py:302-345` — wsl_search_datasets hat ausführlichen Docstring, aber kein description-Argument im Decorator

### Risk Description

LLM-Tool-Selection wird unpräziser, weil es keine standardisierten Anchor-Token für Use-Case-Matching hat. Bei Multi-Server-Setups (siehe README "Combination with Other MCP Servers") wird die Wahl zwischen WSL- und z.B. Zurich-OpenData-Tools schwerer.

### Remediation

Pro Tool das `description=`-Argument explizit setzen mit `<use_case>`/`<important_notes>`/`<example>`-Strukturierung. Die bestehenden Docstrings können als Quelle dienen.

### Effort Estimate

**S–M** — 12 Tools × ~5min = 1h, plus 1 Schema-Review = halbe Tagesarbeit.

### Dependencies / Blockers

Keine.

### Verification After Fix

- `grep -rE '<use_case>' src/`: ≥12 matches
- Re-Audit ARCH-002 zeigt pass


### ARCH-003

# Finding: ARCH-003 — «Not Found» Anti-Pattern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.x |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`src/wsl_envidat_mcp/server.py:286` gibt bei leerem Resultat den Klartext zurück: `"Keine Datensätze gefunden. Bitte Suchbegriff anpassen."`. Nur `wsl_get_avalanche_data` hat einen Fallback ohne org-Filter (server.py:777-781) — kein anderes Tool versucht aktiv eine Heuristik.

### Expected Behavior

Bei "Not Found" sollte das Tool dem LLM einen umsetzbaren Hinweis liefern statt nur einer leeren Antwort:

```python
@mcp.tool()
async def wsl_search_datasets(params):
    result = await ckan_package_search(...)
    if result.get("count", 0) == 0:
        # Heuristik: ähnliche Tags vorschlagen
        suggestions = await ckan_tag_list(query=params.query[:4])
        return {
            "count": 0,
            "results": [],
            "match_type": "none",
            "suggestions": suggestions[:5],
            "hint": "Try one of the suggestions or use wsl_list_tags to browse."
        }
```

### Evidence

- File: `src/wsl_envidat_mcp/server.py:285-286`
- File: `src/wsl_envidat_mcp/server.py:777-781` — einziger Fallback (avalanche)
- Restliche 11 Tools haben keinen Empty-Result-Fallback

### Risk Description

LLM erhält "Keine Datensätze gefunden" und gibt das 1:1 an den User weiter. User probiert nicht erneut, Use-Case scheitert obwohl die Daten in EnviDat existieren (typischerweise unter anderem Begriff). Conversion-Rate des Servers sinkt.

### Remediation

1. `_format_search_results` ergänzen mit optionaler suggestion-Logik basierend auf `wsl_list_tags`
2. Pro Tool prüfen, ob ein semantischer Fallback existiert (avalanche → snow; forest → wald; etc.)
3. README "Known Limitations"-Sektion erweitern mit Hinweis auf Suche-Strategien

### Effort Estimate

**M** — 1-3 Tage (12 Tools × Fallback-Logik + Tests).

### Dependencies / Blockers

Bestens kombinierbar mit OBS-001 (strukturierte Tool-Returns).

### Verification After Fix

- Aufruf mit `query="xyzabc"` (kein Match) liefert `suggestions` oder `hint`
- Re-Audit ARCH-003 zeigt pass


### ARCH-006

# Finding: ARCH-006 — Tool-Budget

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `ARCH-006` |
| **PDF-Reference** | Sec 2.x |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

12 Tools — am oberen Rand des akzeptablen Bereichs (8-15). Drei thematische Tools (`wsl_get_avalanche_data`, `wsl_get_forest_data`, `wsl_get_naturgefahren_data`) sind High-Level-Use-Case-Wrapper, das ist Pass-Pattern.

Aber: `wsl_search_datasets`, `wsl_get_dataset`, `wsl_list_organizations`, `wsl_get_organization`, `wsl_list_tags` sind 1:1-Wrapper um CKAN-Endpoints. Zusätzlich überlappen drei Such-Tools (`wsl_search_datasets`, `wsl_search_by_domain`, `wsl_search_by_location`) in ihrem Use-Case-Spektrum.

### Expected Behavior

Zwei Konsolidierungs-Achsen:

1. **Resources statt Tools** für statische Listen — `wsl_list_organizations`, `wsl_list_tags` könnten Resources werden (`envidat://organizations`, `envidat://tags?prefix=...`).

2. **Such-Konsolidierung:** Ein smarter `wsl_search` mit optionalen Parametern statt drei Tools:
```python
class SearchInput(BaseModel):
    query: str | None = None
    domain: WSLDomain | None = None
    bbox: BBox | None = None  # min_lon, min_lat, max_lon, max_lat
    organization: str | None = None
    limit: int = 10
```

Damit fällt das Tool-Budget auf realistische 6-7.

### Evidence

- File: `src/wsl_envidat_mcp/server.py:302, 350, 450, 505, 556, 605, 665, 704, 744, 794, 842, 893`
- `grep -cE '@mcp\\.tool' src/wsl_envidat_mcp/server.py` → 12
- Drei Such-Tools, drei thematische Domain-Tools, drei Listing-Tools, drei Detail-Tools

### Risk Description

1. LLM-Tool-Selection wird unsicher zwischen `wsl_search_datasets("forest")` vs. `wsl_search_by_domain("wald")` vs. `wsl_get_forest_data()` — alle drei liefern überlappende Resultate
2. Bei Portfolio-Aggregation (mehrere MCP-Server zusammen) frisst der WSL-Server überproportional viel Tool-Budget im LLM-Kontext
3. Bei künftigen Erweiterungen (z.B. Time-Series-Tool) wird die Budget-Inflation strukturell

### Remediation

**Schritt 1 (S):** `wsl_list_organizations` und `wsl_list_tags` als Resources zusätzlich anbieten (Tools bleiben für Backward-Compat).

**Schritt 2 (M):** Neuer `wsl_search` als unifiziertes Such-Tool. Bestehende Such-Tools deprecaten, aber 1 Major-Release lang als thin wrapper behalten.

**Schritt 3 (S):** Klare README-Tabelle "Welches Tool für welchen Use-Case" — explizit, welches Such-Tool wann zu wählen ist.

### Effort Estimate

**M** — 1-3 Tage (Refactoring + Deprecation-Warnings + Tests).

### Dependencies / Blockers

Vorsicht: Breaking-Change-Risiko für bestehende Claude-Desktop-Konfigurationen. Major-Bump (0.x → 0.next.0) und CHANGELOG-Eintrag.

### Verification After Fix

- `grep -cE '@mcp\\.tool' src/`: ≤ 8
- README hat klare Use-Case-Tabelle
- Re-Audit ARCH-006 zeigt pass


### ARCH-012

# Finding: ARCH-012 — protocolVersion-Pinning

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Sec 2.x |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`src/wsl_envidat_mcp/server.py:48-58` initialisiert FastMCP ohne `protocol_version`-Argument:

```python
mcp = FastMCP(
    "wsl-envidat-mcp",
    instructions=(...),
)
```

`pyproject.toml:26` pinnt nur `mcp>=1.3.0` (open-ended). Bei einem `pip install --upgrade mcp` kann das Protokoll auf eine neuere Spec-Version wechseln, ohne dass das im Code sichtbar ist.

### Expected Behavior

Explizites Pinning auf eine getestete Spec-Version:

```python
PROTOCOL_VERSION = "2025-06-18"

mcp = FastMCP(
    "wsl-envidat-mcp",
    protocol_version=PROTOCOL_VERSION,
    instructions=(...),
)
```

Plus Upper-Bound im SDK-Pin: `mcp>=1.3.0,<2.0.0`.

### Evidence

- File: `src/wsl_envidat_mcp/server.py:48-58`
- File: `pyproject.toml:26`
- `grep -rE 'protocol_version|PROTOCOL_VERSION' src/`: 0 matches

### Risk Description

1. SDK-Update kann unbemerkt Protocol-Breaking-Changes einführen
2. CHANGELOG zeigt nicht, gegen welche Spec-Version getestet wurde
3. Bei Bug-Report wird schwer rekonstruierbar, welche Protocol-Variante der User benutzt hat

### Remediation

1. `src/wsl_envidat_mcp/server.py`:
```diff
+ PROTOCOL_VERSION = "2025-06-18"  # MCP-Spec gegen die dieser Server getestet wurde

  mcp = FastMCP(
      "wsl-envidat-mcp",
+     protocol_version=PROTOCOL_VERSION,
      instructions=(...),
  )
```

2. `pyproject.toml`:
```diff
- "mcp>=1.3.0",
+ "mcp>=1.3.0,<2.0.0",
```

3. `CHANGELOG.md` Eintrag: "Pinned MCP protocol version 2025-06-18"

### Effort Estimate

**S** — < 30min.

### Dependencies / Blockers

Prüfen, welche Spec-Version `mcp>=1.3.0` aktuell standardmäßig spricht — die als Pin verwenden.

### Verification After Fix

- `grep protocol_version src/`: 1+ match
- pip install zeigt SDK-Range mit Upper-Bound
- Re-Audit ARCH-012 zeigt pass


### CH-004

# Finding: CH-004 — OGD-CH Lizenz-Compliance

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `CH-004` |
| **PDF-Reference** | Custom (OGD-CH) |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

- README.md:237 nennt "EnviDat Terms of Use ... published under various open licenses (Creative Commons, CC0)"
- `wsl_get_dataset` extrahiert `pkg.get('license_title')` und gibt es als Markdown-Zeile aus (server.py:388, 404)
- Aber: kein strukturiertes `source`/`license`/`provenance`-Feld in Tool-Returns
- JSON-Output von `_format_search_results` (server.py:262-283) enthält weder `license` noch `source`
- Domain-/Avalanche-/Forest-/Naturgefahren-Tools haben keinen License-Hinweis

### Expected Behavior

```python
from pydantic import BaseModel
from typing import Literal

class EnviDatResponse(BaseModel):
    source: str = "EnviDat / WSL (envidat.ch)"
    license: Literal["various open licenses (per dataset)"] | str
    provenance: Literal["live_api"]
    retrieved_at: str
    results: list[dict]
```

LLM bekommt damit konsistente Lizenz-/Source-Information und kann sie korrekt zitieren.

### Evidence

- File: `src/wsl_envidat_mcp/server.py:262-283` — JSON-Output ohne license-Feld
- `grep -nE '"source"|"license"|provenance|attribution' src/wsl_envidat_mcp/*.py`: 0 matches
- File: `src/wsl_envidat_mcp/server.py:388` — license_title nur in Markdown-Branch

### Risk Description

1. LLM zitiert WSL/EnviDat-Daten ohne Lizenz-Attribution — Verstoss gegen CC-BY-Pflicht bei Weiterverwendung
2. Bei JSON-Output (z.B. für Pipelines) fehlt die Lizenz komplett
3. OGD-Best-Practice (opendata.swiss) verlangt Provenance-Information

### Remediation

1. `_format_search_results` JSON-Branch ergänzen:
```python
return json.dumps({
    "source": "EnviDat / WSL",
    "license": "various open licenses (per dataset, see metadata)",
    "provenance": "live_api",
    "retrieved_at": datetime.utcnow().isoformat(),
    "total_found": count,
    "shown": shown,
    "datasets": [
        {
            ...,
            "license": p.get("license_title"),
            "url": f"{ENVIDAT_PORTAL}/dataset/{p.get('name')}",
        } for p in packages
    ],
}, indent=2, ensure_ascii=False)
```

2. README "Safety & Limits"-Sektion deutlich erweitern um eine CC-BY-Attribution-Pflicht-Notiz für Konsumenten der Daten.

### Effort Estimate

**S** — < 1 Tag (1 Funktion + README-Ergänzung).

### Dependencies / Blockers

Keine.

### Verification After Fix

- `wsl_search_datasets(response_format="json")` enthält `source`, `license`, `provenance`, `retrieved_at`
- Re-Audit CH-004 zeigt pass


### OBS-001

# Finding: OBS-001 — Protocol vs. Execution Errors

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Alle Tool-Handler in `src/wsl_envidat_mcp/server.py` haben das Pattern:

```python
try:
    result = await ckan_package_search(...)
    return _format_search_results(result, params.response_format, ...)
except Exception as e:
    return handle_api_error(e, "wsl_search_datasets")
```

`handle_api_error` (`src/wsl_envidat_mcp/api_client.py:120-136`) gibt einen **plain string** zurück, z.B. `"[wsl_search_datasets] Fehler: Zeitüberschreitung. Bitte erneut versuchen."`. Das wird vom Tool als ganz normale Erfolgsantwort an den Client ausgeliefert.

### Expected Behavior

Best-Practice unterscheidet zwei Fehlerklassen:
1. **Protocol-Errors** — `raise` (Server-Bug, Protocol-Verletzung)
2. **Execution-Errors** — strukturiert als `{isError: True, content: [TextContent(...)]}` zurückgeben, damit der MCP-Client den Fehler maschinell erkennt und passend reagiert

```python
from mcp.types import TextContent

@mcp.tool()
async def wsl_search_datasets(params):
    try:
        result = await ckan_package_search(...)
        return _format_search_results(...)
    except httpx.TimeoutException:
        return {
            "isError": True,
            "content": [TextContent(
                type="text",
                text="EnviDat-API: Timeout. Versuche es in 30s erneut."
            )],
        }
```

### Evidence

- File: `src/wsl_envidat_mcp/server.py:343-344, 442-443, ...` — alle 12 Tools nutzen das Plain-String-Return-Pattern
- File: `src/wsl_envidat_mcp/api_client.py:120-136` — `handle_api_error` gibt str zurück

### Risk Description

1. Client kann Erfolg nicht zuverlässig von Fehler unterscheiden — LLM bekommt einen "Fehler-Text" als wäre er das gesuchte Ergebnis und kann darauf falsche Schlüsse aufbauen
2. Retry-Logik im Client funktioniert nicht — der Client sieht keinen `isError`-Flag und retryt nicht bei transienten Fehlern wie Timeout/429
3. Bei künftiger Monitoring-Anbindung (Tool-Success-Rate Dashboard) zählen alle 200-OK-mit-Error-String als Erfolg

### Remediation

1. Helper in `api_client.py` ergänzen:
```python
from mcp.types import TextContent

def error_response(message: str) -> dict:
    return {"isError": True, "content": [TextContent(type="text", text=message)]}
```

2. In jedem Tool das `except`-Branch umstellen:
```diff
- except Exception as e:
-     return handle_api_error(e, "wsl_search_datasets")
+ except Exception as e:
+     return error_response(handle_api_error(e, "wsl_search_datasets"))
```

3. Optional: spezifische Exception-Klassen unterscheiden (Timeout → retryable, 404 → nicht retryable) und das im `content`-Hint kommunizieren

### Effort Estimate

**S–M** — 1–2 Tage (1 Helper + 12 Tool-Migrationen + Tests).

### Dependencies / Blockers

Keine, aber sinnvoll vor OPS-001 (Unit-Tests prüfen dann gleich das neue Format).

### Verification After Fix

- Tool-Output bei Fehlern ist `dict` mit `isError: True`, nicht `str`
- Unit-Tests gegen 404/Timeout/429 erwarten das neue Format
- Re-Audit OBS-001 zeigt pass


### OBS-003

# Finding: OBS-003 — Structured Logging

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6 + Anhang B10 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`src/wsl_envidat_mcp/server.py:39-43`:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
```

Standard stdlib-logging mit Plain-String-Output. Keine `structlog`/`loguru`/`pino` in `pyproject.toml:25-29`.

### Expected Behavior

Strukturierte JSON-Logs mit bound context (tool, request_id, ggf. user_id), RFC-5424-Severity-Stufen, maschinen-parsbar für SIEM-Tools:

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger("mcp.wsl-envidat")
log = logger.bind(tool="wsl_search_datasets", query=params.query)
log.info("search.start")
```

### Evidence

- File: `src/wsl_envidat_mcp/server.py:39-43`
- `grep -E 'structlog|loguru' pyproject.toml`: 0 matches
- `grep -rE 'logger\\.bind|logger\\.info|extra=' src/`: keine bound-context-Aufrufe

### Risk Description

1. Logs sind nicht maschinen-aggregierbar — bei SIEM-Anbindung (Datadog, Splunk, ELK) Parser-Aufwand pro Feld
2. Kein Request-ID-Tracing über mehrere Tool-Calls hinweg — schwer zu debuggen bei produktiven Issues
3. Severity-Mapping zu RFC 5424 (notice/warning/critical/alert) fehlt — Alerting-Regeln müssen über String-Patterns laufen

### Remediation

1. `pyproject.toml`:
```diff
 dependencies = [
     "mcp>=1.3.0",
     "httpx>=0.27.0",
     "pydantic>=2.0.0",
+    "structlog>=24.1.0",
 ]
```

2. Logging-Init in `server.py` ersetzen:
```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)
logger = structlog.get_logger("mcp.wsl-envidat")
```

3. In jedem Tool: `log = logger.bind(tool="<name>", **{...key-args...})`

### Effort Estimate

**S** — < 1 Tag (1 Dependency, Init-Block, optional bind() in Tool-Bodies).

### Dependencies / Blockers

Keine.

### Verification After Fix

- `pip install -e .` zieht structlog
- Server-Start gibt JSON-Log auf stderr
- Re-Audit OBS-003 zeigt pass


### OPS-001

# Finding: OPS-001 — Test-Strategie

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`tests/`-Verzeichnis enthält ausschliesslich Live-Skripte:
- `tests/test_integration.py` (asyncio-Skript, ruft envidat.ch direkt)
- `tests/test_20_szenarien.py` (20 Live-Szenarien gegen die echte API)

CI führt nur `python tests/test_integration.py` aus (`.github/workflows/ci.yml:41`). README behauptet zwar `PYTHONPATH=src pytest tests/ -m "not live"` (README.md:248), aber kein einziger Test trägt einen `@pytest.mark.live`-Marker und es existiert kein `tests/test_unit.py` mit gemockter HTTP-Schicht.

### Expected Behavior

```
tests/
├── test_unit.py          # respx/pytest-httpx, kein Netz, ≥1 Test pro Tool
├── test_live.py          # @pytest.mark.live, gegen envidat.ch
└── conftest.py           # gemeinsame Fixtures
```

CI führt standardmässig `pytest -m "not live"` aus; Live-Tests laufen nur in einem separaten gated Job (z.B. nightly).

### Evidence

- `ls tests/`: `__init__.py  test_20_szenarien.py  test_integration.py`
- `grep -E '@pytest\.mark|respx|httpx_mock' tests/`: 0 matches
- `pyproject.toml:32-36`: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `ruff>=0.4.0` — kein `respx`, kein `pytest-httpx`
- `.github/workflows/ci.yml:41`: `python tests/test_integration.py` statt `pytest`

### Risk Description

1. **CI-Flakiness:** Jeder envidat.ch-Ausfall oder jede Latenz-Spitze bricht den CI-Lauf — Pipeline-Vertrauen sinkt, Reviews ignorieren Failures
2. **Regression-Lücke:** Edge-Cases (Timeout, 429, malformed JSON) lassen sich gegen Live-API nicht reproduzierbar testen
3. **Refactoring-Bremse:** Ohne Unit-Tests blockiert jede Code-Änderung auf "warten bis envidat.ch antwortet"
4. **Dependency-Pin auf externe Verfügbarkeit:** Test-Setup ist nicht hermetisch — Skill OPS-001 Pass-Pattern verlangt "mocked + live separat"

### Remediation

1. `pyproject.toml` dev-deps ergänzen:
```diff
 dev = [
     "pytest>=8.0.0",
     "pytest-asyncio>=0.23.0",
+    "respx>=0.21.0",
     "ruff>=0.4.0",
 ]
```

2. `tests/conftest.py` mit Fixture für CKAN-Mock-Responses:
```python
import pytest
import respx
from httpx import Response

@pytest.fixture
def mock_envidat():
    with respx.mock(base_url="https://www.envidat.ch/api/action") as mock:
        yield mock
```

3. `tests/test_unit.py` — pro Tool 1-3 Tests gegen das gemockte API
4. `tests/test_live.py` — bestehende Szenarien migrieren, jeweils mit `@pytest.mark.live`
5. `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = ["live: requires live API access"]
```

6. `.github/workflows/ci.yml`: Default-Job ohne live, separater nightly-Job für live

### Effort Estimate

**M** — 1–3 Tage (12 Tools × 1-2 Unit-Tests + Migration + CI-Anpassung).

### Dependencies / Blockers

Keine.

### Verification After Fix

- `pytest -m "not live"` läuft ohne Netz-Zugriff durch
- `pytest -m live` läuft gegen envidat.ch
- CI-Default-Job ist offline-fähig
- `respx` als dev-Dep erkennbar in pyproject.toml
- Re-Audit OPS-001 zeigt pass


### OPS-002

# Finding: OPS-002 — Doku-Standard

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `OPS-002` |
| **PDF-Reference** | Anhang C |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

- README.md (EN) und README.de.md (DE) beide vorhanden ✓
- ASCII-Architekturdiagramm vorhanden (README.md:160-172) ✓
- Alle Pflicht-Sektionen vorhanden: Overview/Features/Prerequisites/Installation/Quickstart/Configuration/Tools/Resources/Architecture/Project Structure/Limitations/Safety & Limits/Testing/Changelog/Contributing/License ✓
- Anchor-Demo-Query nur in README.md (EN, Zeile 25) — fehlt in README.de.md
- Keine "Phase"-Sektion (siehe OPS-003)

### Expected Behavior

- Anchor-Demo-Query in beiden README-Sprachen 1:1 entsprechend
- Optional: separate "## Anker-Demo-Frage"-Sektion statt nur als Zitat in der Übersicht

### Evidence

- `grep -iE 'anchor|beispiel.frage|example.question' README.de.md`: 0 matches
- `grep -iE 'anchor demo query|anchor query' README.md`: 1 match (Zeile 25)

### Risk Description

Geringes Risiko — kosmetisch / Doku-Konsistenz. Bei DE-sprachigen Stakeholdern (Stadt-Zürich-GL, KI-Fachgruppe) fehlt der konkrete Demo-Anker, was die Erstrezeption erschwert.

### Remediation

README.de.md ergänzen mit dem deutschen Pendant des englischen Demo-Beispiels:

```markdown
> **Anker-Demo-Frage:** *"Wie war die Luftqualität und Waldgesundheit
> rund um das Schulhaus Leutschenbach in Zürich — und was sagt die WSL
> aktuell zum Waldzustand im Kanton?"*
```

### Effort Estimate

**S** — < 1h.

### Dependencies / Blockers

Keine.

### Verification After Fix

- README.de.md enthält Anker-Demo-Frage
- Re-Audit OPS-002 zeigt pass


### OPS-003

# Finding: OPS-003 — Phasenarchitektur

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Der Server ist verhaltens-seitig eindeutig Phase 1 (Read-only Wrapper): alle 12 Tools haben `readOnlyHint=True, destructiveHint=False`. README erwähnt aber keine "Phase"-Sektion und auch keine `docs/roadmap.md`.

### Expected Behavior

Im README explizit deklarieren:

```markdown
## Phase

Dieser Server befindet sich in **Phase 1: Read-only Wrapper**.

| Eigenschaft | Status |
|---|---|
| Read-Tools | ✅ 12 Tools, alle `readOnlyHint: true` |
| Write-Tools | ❌ keine (nicht geplant, Public Data ist read-only) |
| Semantic Layer | ⚠️ teilweise (3 Domain-Tools aggregieren kuratiert) |
| OAuth | ❌ nicht erforderlich (Public Open Data, kein API-Key) |
| Audit-Run | ✅ 2026-05-27, mcp-audit-skill v1.0.0 |
```

Plus `docs/roadmap.md` für Phase-2/3 (Multi-Source-Aggregation, Caching-Layer, etc.).

### Evidence

- `grep -iE 'phase|read.only.first|wrapper' README.md README.de.md docs/`: 0 matches
- `find . -iname '*roadmap*'`: nicht vorhanden
- `src/wsl_envidat_mcp/server.py`: 12 × `readOnlyHint=True`, 0 × `destructiveHint=True`

### Risk Description

1. Externe Stakeholder (Stadt-Zürich-Compliance, GL) können den Reifegrad nicht einschätzen
2. Bei Portfolio-Migration zu Phase-2/3 fehlt der Trace, wann der Switch passierte
3. Bei Re-Audit ist nicht ersichtlich, wann der letzte Audit-Run war und welche Skill-Version verwendet wurde

### Remediation

1. README "Phase"-Sektion einfügen (siehe Expected Behavior)
2. `docs/roadmap.md` anlegen mit Skizze für etwaige Phase-2 (z.B. Caching-Layer für stark-frequentierte Datasets, Semantic-Layer-Tool das Forest+Snow+Hazard zu einer Lage-Übersicht aggregiert)
3. Audit-Run-Tabelle im README pflegen (Datum, Skill-Version, Result)

### Effort Estimate

**S** — < 1 Tag (Doku).

### Dependencies / Blockers

Keine.

### Verification After Fix

- README enthält "## Phase"-Sektion
- `docs/roadmap.md` existiert
- Re-Audit OPS-003 zeigt pass


### SCALE-002

# Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`src/wsl_envidat_mcp/server.py:1037-1038` startet Streamable-HTTP via `mcp.run(transport="streamable_http", port=port)`. Keine Deployment-Manifeste im Repo:
- `railway.toml` / `render.yaml` / `fly.toml`: nicht vorhanden
- `k8s/`, `helm/`, `Dockerfile`: nicht vorhanden
- README "Cloud Deployment"-Sektion (README.md:107-114) erwähnt nur das CLI-Kommando, nicht die Sticky-Session-Anforderung

### Expected Behavior

Bei Multi-Replica-Deployment muss derselbe Client immer denselben Pod erreichen, sonst geht der Session-State verloren. Best-Practice je nach Plattform:

- **Railway/Render:** Single-Replica oder sticky cookie aktivieren
- **Kubernetes:** `sessionAffinity: ClientIP` im Service oder `nginx.ingress.kubernetes.io/affinity: cookie`
- **Cloudflare Workers:** Durable Objects als Shared-State-Layer

README muss die Anforderung explizit dokumentieren, damit Cloud-Deployer es nicht versehentlich falsch konfigurieren.

### Evidence

- `ls /home/user/wsl-envidat-mcp/`: keine Deployment-Manifeste
- File: `README.md:107-114` — Cloud Deployment beschreibt nur den Start-Command
- `grep -rE 'stick|sessionAffinity|session.affinity' .`: 0 matches

### Risk Description

Praktisch nur relevant, sobald ein Multi-Replica-Cloud-Deployment betrieben wird. Aktuell ist `is_cloud_deployed: false` — Finding wird trotzdem geöffnet, weil:
1. README aktiv für Cloud-Deployment wirbt ("for use via claude.ai in the browser")
2. Default-Setup auf Railway/Render skaliert nach 2 Replikaten automatisch — User würde unwissend in den Bug laufen
3. Symptom ist subtil (Session "fehlt sporadisch") und schwer zu debuggen

### Remediation

1. README "Cloud Deployment"-Sektion erweitern:
```markdown
> ⚠️ **Sticky-Sessions erforderlich:** Streamable HTTP führt Session-State im Server.
> Bei Multi-Replica-Deployment muss der Load Balancer Session-Affinity aktiviert haben.
>
> - **Railway/Render:** Bleibe bei 1 Replikat oder aktiviere "Sticky Sessions"
> - **Kubernetes:** `spec.sessionAffinity: ClientIP` im Service
```

2. Optional: `deploy/`-Verzeichnis mit Beispiel-Manifesten anlegen (k8s Service, railway.toml mit `replicas = 1`)

3. Bei Dockerfile (siehe SEC-007): `HEALTHCHECK` ergänzen, der `/health`-Endpoint testet, damit LB richtig routet

### Effort Estimate

**S** — < 1 Tag (Doku-Update + optional Beispiel-Manifest).

### Dependencies / Blockers

Sinnvoll zusammen mit SEC-007 (Dockerfile) erledigen.

### Verification After Fix

- README enthält Warn-Block zu Sticky-Sessions
- Optional: `deploy/`-Verzeichnis mit Beispielen
- Re-Audit SCALE-002 zeigt pass


### SEC-005

# Finding: SEC-005 — DNS-Rebinding-Prevention

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 4.4 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`src/wsl_envidat_mcp/api_client.py:97-107` öffnet pro Request einen neuen `httpx.AsyncClient` mit `base_url="https://www.envidat.ch/api/action"`. Es gibt kein DNS-Pinning — bei jedem Request wird die Domain neu aufgelöst. `follow_redirects=True` (Zeile 106) öffnet zusätzlich ein cross-domain-Redirect-Fenster.

### Expected Behavior

DNS-Auflösung einmalig durchführen, IP-Adresse in der URL pinnen, `Host`-Header explizit setzen:

```python
import socket, ipaddress
from urllib.parse import urlparse

def _resolve_pinned(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    info = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    ip = info[0][4][0]
    if ipaddress.ip_address(ip).is_private:
        raise ValueError("Resolved to private IP")
    return ip, parsed.hostname
```

Plus `follow_redirects=False` für strikte Kontrolle (siehe SEC-021).

### Evidence

- File: `src/wsl_envidat_mcp/api_client.py:97-107` — kein DNS-Pinning
- `grep -rE 'getaddrinfo|gethostbyname|dns\\.resolve' src/`: 0 matches
- File: `src/wsl_envidat_mcp/api_client.py:106` — `follow_redirects=True`

### Risk Description

Praktisch geringes Risiko, weil:
1. Der einzige Target-Host ist envidat.ch (vertrauenswürdige Schweizer Forschungs-Infrastruktur)
2. Keine User-Input-controlled URLs existieren

Theoretisch:
1. Bei DNS-Spoofing/Cache-Poisoning der lokalen Auflösungs-Schicht könnte ein zweiter Lookup eine andere IP liefern als der erste
2. Bei Multi-Pod-Cloud-Deployment mit unterschiedlichen DNS-Stati kann es zu inkonsistentem Verhalten kommen

### Remediation

Da das Risiko durch die hardcoded Single-Host-Architektur stark begrenzt ist:

**Pragmatische Minimal-Variante (S):**
1. `follow_redirects=False` setzen (siehe SEC-021)
2. Im README "Safety & Limits"-Sektion explizit dokumentieren: "Server vertraut der DNS-Auflösung des Host-OS für envidat.ch."

**Vollständige Variante (M), wenn SEC-021 ausgebaut wird:**
1. `safe_fetch`-Helper mit DNS-Pinning aus dem Best-Practice-Pattern (SEC-005 §Pass-Pattern) implementieren
2. Helper überall in `api_client.py` nutzen
3. Unit-Test mit gemockter doppelter DNS-Antwort

### Effort Estimate

- Minimal: **S** (< 1 Tag, eine Flag-Änderung + Doku)
- Voll: **M** (1-3 Tage, mit Helper und Tests)

### Dependencies / Blockers

Sinnvoll als Paket mit SEC-021 angehen.

### Verification After Fix

- `follow_redirects=False` im Code
- Optional: Unit-Test mit DNS-Mock
- Re-Audit SEC-005 zeigt pass


### SEC-007

# Finding: SEC-007 — Container-Sandboxing

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4.5 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Repository enthält keinen `Dockerfile`, kein `docker-compose.yml` und keine k8s/helm-Manifest. Die Distribution erfolgt ausschliesslich via PyPI (`uvx wsl-envidat-mcp` bzw. `pip install`), siehe `pyproject.toml:38-39` und README.md:55-60. Damit läuft der Server stets mit User-Privilegien des aufrufenden Accounts, ohne Filesystem-, Network- oder Syscall-Restriktion.

### Expected Behavior

Defense-in-Depth gegen kompromittierte Dependencies (httpx/pydantic/mcp könnten Supply-Chain-Target werden) verlangt eine Sandbox-Option. Best-Practice:
- Distroless oder `python:3.11-slim` Container-Image mit non-root USER
- `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `runAsNonRoot: true`
- seccomp-Default-Profile
- Image-Build via GitHub Actions, push zu ghcr.io oder Docker Hub

### Evidence

- `ls /home/user/wsl-envidat-mcp/`: kein Dockerfile, kein k8s/-Verzeichnis
- `grep -E 'docker|container' .github/workflows/*.yml`: keine Container-Builds
- `pyproject.toml:38-39` definiert nur den Python-Entry-Point

### Risk Description

1. **Supply-Chain:** Wird `httpx` oder eine Transitiv-Dep kompromittiert, kann beliebiger Code mit den vollen User-Rechten laufen — Read auf `~/.ssh/`, `~/.aws/`, Browser-Cookies
2. **Cloud-Deployment:** Sobald der Server auf Railway/Render läuft, ist ohne Container-Hardening jeder Code-Pfad im Klartext-Filesystem zugänglich
3. **CI/CD:** Ohne reproducible Container-Image gibt es keinen sicheren Distribution-Channel ausserhalb von PyPI

### Remediation

1. `Dockerfile` im Repo-Root anlegen (multi-stage, distroless oder slim):

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --target=/install .

FROM python:3.11-slim
RUN useradd --create-home --uid 1000 mcp
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
USER mcp
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "wsl_envidat_mcp.server"]
```

2. `.github/workflows/container.yml` ergänzen: Build + Push zu ghcr.io bei Release-Tag
3. README "Cloud Deployment"-Sektion: Beispiel mit `docker run --read-only --tmpfs /tmp ghcr.io/malkreide/wsl-envidat-mcp` ergänzen
4. Optional: SBOM-Generierung via `syft` im CI

### Effort Estimate

**M** — 1–3 Tage (Dockerfile + Workflow + README + Smoke-Test).

### Dependencies / Blockers

Keine.

### Verification After Fix

- `docker build .` succeeded
- `docker run --rm wsl-envidat-mcp` startet ohne root
- ghcr.io/malkreide/wsl-envidat-mcp:latest existiert
- Re-Audit SEC-007 zeigt pass


### SEC-009

# Finding: SEC-009 — Session-ID Cryptographic Binding

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Der Server delegiert das gesamte Session-Management an die FastMCP-SDK (mcp>=1.3.0). Im Code existiert kein eigener Session-ID-Generator und keine Verifikation des SDK-Defaults. Bei `auth_model=none` gibt es zudem keine User-Identität, an die eine Session gebunden werden könnte — der vom Best-Practice geforderte Schritt 2 (Format `<user_id>:<session_id>`) ist strukturell nicht erreichbar.

### Expected Behavior

Für Streamable-HTTP-Server muss die Session-ID:
1. Kryptografisch sicher generiert sein (mindestens 256 Bit Entropie, UUIDv4 oder `secrets.token_urlsafe(32)`)
2. An eine validierte User-Identität gebunden sein (`<user_id>:<session_id>`), die aus einem signierten Token kommt

Bei `auth_model=none` ist Schritt 2 nicht umsetzbar — der Server muss dann entweder Auth einführen oder Streamable-HTTP-Deployment explizit als "nicht für Multi-Tenant geeignet" markieren.

### Evidence

- File: `src/wsl_envidat_mcp/server.py:48-58` — FastMCP-Init ohne custom session-handler
- File: `src/wsl_envidat_mcp/server.py:1028-1040` — main() ohne Session-Config
- pyproject.toml: `mcp>=1.3.0` — keine pinned Version, SDK-Default kann beim Upgrade ändern

### Risk Description

Bei einem Streamable-HTTP-Deployment ohne Auth:
- Wer eine Session-ID errät oder via Netzwerk-Mitschnitt abfängt, kann Tool-Calls im Kontext des ursprünglichen Users absetzen
- Da alle Tools read-only und gegen Public Data sind, ist der direkte Schaden begrenzt — aber Logs/Tracing-Daten leaken, und Rate-Limit-Budgets können fremdverbraucht werden
- Bei einer künftigen SDK-Regression in der Session-ID-Generierung bleibt das im Code unbemerkt

### Remediation

Kurz-/Mittelfrist (defensiv ohne Auth):
1. SDK-Version in pyproject.toml pinen auf `mcp>=1.3.0,<2.0.0` und SDK-Default dokumentieren
2. README "Cloud Deployment"-Sektion ergänzen mit Warnung: "Streamable HTTP ohne Reverse-Proxy + Auth ist nur für 1-User-Setups (z.B. claude.ai-Browser eines Einzelnutzers) gedacht. Für Multi-Tenant-Einsatz ist ein vorgelagerter OAuth-Gateway zwingend."
3. Test ergänzen, der zwei aufeinanderfolgende Sessions startet und Entropie der `Mcp-Session-Id`-Header validiert

Langfrist (wenn Multi-Tenant): OAuth-Proxy davorschalten und das Pattern aus SEC-009 §Mitigation umsetzen.

### Effort Estimate

- Kurz/Mittel: **S** (Dokumentation + Pin + Smoke-Test)
- Langfrist mit OAuth: **L** (1-2 Wochen)

### Dependencies / Blockers

Keine für Kurzfrist. Für Langfrist: Klärung, ob Streamable-HTTP-Deployment überhaupt für mehrere User vorgesehen ist (siehe OPS-003 Phasenarchitektur).

### Verification After Fix

- README enthält Multi-Tenant-Warnung
- pyproject.toml zeigt SDK-Range mit Major-Upper-Bound
- Optional: pytest-test, der `secrets.token_urlsafe(32)`-Pattern in der vom SDK gesetzten Session-ID validiert


### SEC-016

# Finding: SEC-016 — 0.0.0.0-Binding-Prevention (NeighborJack)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `SEC-016` |
| **PDF-Reference** | Sec 4.5 |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

`src/wsl_envidat_mcp/server.py:1037-1038` ruft `mcp.run(transport="streamable_http", port=port)` ohne explizites `host`-Argument auf. Das Binding-Verhalten wird damit vollständig der jeweils installierten `mcp`-SDK-Version überlassen.

```python
if transport == "streamable_http":
    mcp.run(transport="streamable_http", port=port)
else:
    mcp.run()
```

Eine grep auf `0.0.0.0` ergibt 0 Treffer in `src/` und in `.github/` — d.h. es gibt keine bewusste Bindung, aber auch keine bewusste Restriktion.

### Expected Behavior

Lokaler Default bindet **explizit** auf `127.0.0.1`. Nur in Container/Cloud-Kontext darf `0.0.0.0` zum Einsatz kommen, und dann gesteuert durch eine ENV-Var. Beispiel-Pattern aus dem Best-Practice-Katalog:

```python
host = os.environ.get("MCP_HOST", "127.0.0.1")  # lokal sicher
if transport == "streamable_http":
    mcp.run(transport="streamable_http", host=host, port=port)
```

### Evidence

- File: `src/wsl_envidat_mcp/server.py:1030-1040`
- Grep-Result: `grep -rE '0\.0\.0\.0' src/ .github/ pyproject.toml` → 0 matches
- README zeigt nur `MCP_TRANSPORT=streamable_http PORT=8000 python -m wsl_envidat_mcp.server` ohne Host-Diskussion (README.md:111)

### Risk Description

Bei Entwicklung in öffentlichen Netzen (Co-Working, Konferenz-WLAN, Hotel) und einer FastMCP-Version mit `0.0.0.0`-Default ist der Server für alle Geräte im selben Subnetz erreichbar — ohne dass der Entwickler das mitbekommt. NeighborJack-Angreifer kann `tools/list` aufrufen und die 12 EnviDat-Tools ausführen, was selbst mit Read-only-Daten zu unerwünschtem Traffic auf die User-IP führt (z.B. Catalog-Scan, Geo-Profilierung des Entwicklers).

Die Severity bleibt `critical` trotz Read-only-Charakter, weil:
1. Der Default ist nicht im Code festgelegt (SDK-abhängig)
2. Bei künftigem Cloud-Deployment ist die Differenzierung lokal/container nicht vorbereitet

### Remediation

```diff
 def main() -> None:
     """Startet den WSL/EnviDat MCP Server."""
     import os

     transport = os.environ.get("MCP_TRANSPORT", "stdio")
     port = int(os.environ.get("PORT", "8000"))
+    host = os.environ.get("MCP_HOST", "127.0.0.1")  # 0.0.0.0 nur via expliziter Env-Var

     logger.info("WSL/EnviDat MCP Server startet (Transport: %s)", transport)

     if transport == "streamable_http":
-        mcp.run(transport="streamable_http", port=port)
+        mcp.run(transport="streamable_http", host=host, port=port)
     else:
         mcp.run()
```

README ergänzen mit Hinweis in der Cloud-Deployment-Sektion: `MCP_HOST=0.0.0.0` ist nur in Container-Kontexten erforderlich (Container-Netzwerk-Isolation), nie lokal.

### Effort Estimate

**S** — < 1 Tag, 1 Codezeile + 1 README-Block + 1 Test.

### Dependencies / Blockers

Keine.

### Verification After Fix

- Re-Audit SEC-016
- Bash-Test: `MCP_TRANSPORT=streamable_http python -m wsl_envidat_mcp.server &` dann `ss -tlnp | grep 8000` → erwartet `127.0.0.1:8000`, nicht `0.0.0.0:8000`
- README enthält Sektion zur Host-Differenzierung


### SEC-021

# Finding: SEC-021 — Egress-Allow-List

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Sec 4.x |
| **Audit-Datum** | 2026-05-27 |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Die einzige externe Domain ist hardcoded in `src/wsl_envidat_mcp/api_client.py:20`:
```python
ENVIDAT_API_BASE = "https://www.envidat.ch/api/action"
```

`_make_client` (api_client.py:97-107) setzt `follow_redirects=True`. Es gibt keine explizite Allow-List, keine Redirect-Domain-Validierung und keine Network-Policy-Dokumentation.

### Expected Behavior

Code-Layer Allow-List, plus dokumentierte Network-Layer-Restriktion fürs Deployment:

```python
ALLOWED_HOSTS = frozenset({"www.envidat.ch", "envidat.ch"})

def _assert_host_allowed(url: str) -> None:
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise PermissionError(f"Host not in allow-list: {host}")
```

Plus: bei Cloud-Deployment im README erwähnen, dass Container-Egress auf `*.envidat.ch:443` zu beschränken ist (NetworkPolicy / Cloudflare-Egress-Rule).

### Evidence

- File: `src/wsl_envidat_mcp/api_client.py:20` — Single Base-URL hardcoded
- File: `src/wsl_envidat_mcp/api_client.py:106` — `follow_redirects=True`
- `grep -rE 'allowed_(domains|hosts|origins)|host_whitelist' src/`: 0 matches

### Risk Description

1. **Redirect-Hijack:** Sollte envidat.ch (oder ein Upstream-Reverse-Proxy) jemals einen 302 zu einer fremden Domain ausliefern, folgt httpx blind dort hin. Bei kompromittiertem Upstream wäre das ein Cross-Origin-Datenleck-Vektor
2. **Künftige Multi-Source-Erweiterung:** Sobald jemand z.B. `slf.ch` als zweite Quelle einbaut, fehlt das Pattern, um diese explizit zu listen — Drift in Richtung "alle Domains erlaubt" passiert leise
3. **Network-Layer:** Auf Deployment-Ebene gibt es keine erzwungene Egress-Allow-List — bei Cloud-Deployment in Default-VPC könnte ein supply-chain-kompromittierter Code beliebig hinaus telefonieren

### Remediation

1. `api_client.py`:
```python
from urllib.parse import urlparse

ALLOWED_HOSTS = frozenset({"www.envidat.ch", "envidat.ch"})

def _assert_host_allowed(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise PermissionError(f"Host not in allow-list: {host}")

def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=ENVIDAT_API_BASE,
        timeout=REQUEST_TIMEOUT,
        headers={...},
        follow_redirects=False,  # strikte Kontrolle
    )
```

2. README "Cloud Deployment"-Sektion erweitern: Empfehlung für NetworkPolicy/Egress-Rule (Beispiel-yaml für k8s).

3. Optional: bei Redirect-Bedarf manuelles handling mit explizitem `_assert_host_allowed(response.headers["location"])`.

### Effort Estimate

**S** — < 1 Tag (Code + README + 1 Test).

### Dependencies / Blockers

Keine. Sinnvoll zusammen mit SEC-005 (DNS-Pinning) anzugehen.

### Verification After Fix

- Unit-Test mit `respx`-Mock, der einen 302 zu attacker.com ausliefert → erwartet `PermissionError`
- `follow_redirects=False` im Code
- README mit Network-Policy-Beispiel
- Re-Audit SEC-021 zeigt pass


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-009** (critical, partial)
2. **SEC-016** (critical, partial)
3. **ARCH-006** (high, partial)
4. **OBS-001** (high, partial)
5. **OPS-001** (high, fail)
6. **OPS-003** (high, partial)
7. **SCALE-002** (high, partial)
8. **SEC-005** (high, partial)
9. **SEC-007** (high, fail)
10. **SEC-021** (high, partial)
11. **ARCH-002** (medium, partial)
12. **ARCH-003** (medium, partial)
13. **ARCH-012** (medium, partial)
14. **CH-004** (medium, partial)
15. **OBS-003** (medium, fail)
16. **OPS-002** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| policy | `fail-or-partial` |


_Generated by tools/build_report.py — do not edit by hand._
