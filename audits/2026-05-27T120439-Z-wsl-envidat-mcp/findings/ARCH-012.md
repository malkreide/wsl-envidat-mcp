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
