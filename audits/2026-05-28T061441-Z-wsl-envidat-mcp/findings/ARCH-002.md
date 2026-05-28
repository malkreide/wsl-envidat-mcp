# Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open (carried-over, partial) |
| **Server** | `wsl-envidat-mcp` |
| **Check-Reference** | `ARCH-002` |
| **Audit-Datum** | 2026-05-28 (Re-Audit) |
| **Auditor** | Hayal Oezkan (via mcp-audit-skill v1.0.0) |

### Observed Behavior

Bei v0.2.0 (PR #6) wurden `<use_case>`/`<important_notes>`/`<example>`-Tags
an die vier routing-sensitiven Tools angefügt (`wsl_search`, `wsl_get_dataset`,
zwei davon sind seit ARCH-006 ohnehin in `wsl_search` aufgegangen). Die
verbleibenden 6 Tools (`wsl_list_organizations`, `wsl_get_organization`,
`wsl_list_tags`, `wsl_get_recent_datasets`, `wsl_get_avalanche_data`,
`wsl_get_forest_data`, `wsl_get_naturgefahren_data`, `wsl_catalog_stats`)
haben weiterhin nur den Auto-generated `description=` aus dem Docstring.

### Expected Behavior

Alle Tools haben strukturierte Tags in `description=` für maximale
LLM-Tool-Selection-Klarheit.

### Risk Description

Praktisch gering: die verbleibenden Tools haben domain-eindeutige Namen
(`wsl_get_avalanche_data` etc.) und readOnlyHint=True — sie sind kaum
mit anderen Tools verwechselbar. Der Befund bleibt aber offen, um
Konsistenz im LLM-Routing weiter zu verbessern.

### Remediation

Nachtrag der Tags an die 6 verbleibenden Tools. Effort: **S** (<1h).
Geplant für eine spätere Hygiene-Iteration oder im Rahmen von Phase-2-Arbeit.

### Verification After Fix

- `grep -rE '<use_case>' src/` → ≥10 matches
- Re-Audit ARCH-002 zeigt pass
