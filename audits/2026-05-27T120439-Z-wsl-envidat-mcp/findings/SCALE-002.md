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
