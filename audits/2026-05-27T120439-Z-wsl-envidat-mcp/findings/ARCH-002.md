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
