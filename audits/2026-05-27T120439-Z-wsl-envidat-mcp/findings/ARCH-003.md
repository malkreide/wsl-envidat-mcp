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
