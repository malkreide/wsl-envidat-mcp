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
