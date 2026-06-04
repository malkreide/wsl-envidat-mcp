# Sicherheitsrichtlinie & Sicherheitslage

[🇬🇧 English Version](SECURITY.md)

`wsl-envidat-mcp` wurde gegen den internen MCP-Best-Practice-Audit-Katalog
(`mcp-audit-skill` v1.0.0) gehärtet. Dieses Dokument fasst die Sicherheitslage
zusammen und dokumentiert die **akzeptierten Risiken** für Kontrollen, die
bewusst auf der Portfolio-/Gateway-Ebene statt innerhalb dieses einzelnen
Servers behandelt werden.

## Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie die in `README.md` genannte verantwortliche Person. Erstellen
Sie für ausnutzbare Schwachstellen **keine** öffentlichen Issues.

## Zusammenfassung der Sicherheitslage

Dies ist ein **rein lesender**, **PII-freier** MCP-Server für **öffentliche Open
Data**. Alle 10 Tools fragen ausschliesslich die offizielle EnviDat CKAN API
(WSL — Eidg. Forschungsanstalt für Wald, Schnee und Landschaft) unter
`envidat.ch` ab. Bereits umgesetzte Härtungsmassnahmen:

| Bereich | Kontrolle |
|---|---|
| Egress | HTTPS-erzwungene Allow-List ausschliesslich für feste EnviDat-Hosts (`ALLOWED_HOSTS` in `api_client.py`, SEC-021) |
| Redirects | `follow_redirects=False` schliesst das Cross-Origin-Redirect-Hijack-Fenster (SEC-005/SEC-021) |
| TLS | Zertifikatsverifizierung standardmässig aktiv (`httpx`-Default) |
| Binding | Netzwerk-Transporte binden standardmässig an `127.0.0.1`; `0.0.0.0` nur via explizitem `MCP_HOST` im Container (SEC-016) |
| Input | Pydantic-v2-Validierung an allen Tool-Grenzen (SEC-018) |
| Secrets | Keine erforderlich — nur nicht-geheime Umgebungsvariablen, `.gitignore` schützt `.env`, keine hartcodierten Secrets (ARCH-005/SEC-013) |
| Fehler | Upstream-Antworten werden nach stderr geloggt, niemals an das Modell weitergegeben (OBS-002) |
| Stdout | Reserviert für den JSON-RPC-Stream; strukturiertes Logging fest auf stderr (OBS-003/OBS-004) |
| Container | Gehärtetes Multi-Stage-Image, läuft als non-root (`uid=1000`), keine Build-Tools im Runtime-Layer |

Die zugrunde liegenden Audit-Berichte finden Sie unter `audits/` (letzter Run:
2026-05-28, 31/32 Checks bestanden, 0 critical/high) und die Härtungshistorie in
`CHANGELOG.md`.

## Akzeptierte Risiken (Kontrollen auf Portfolio-Ebene)

Die folgenden Audit-Prüfungen sind **bewusst nicht** innerhalb dieses Servers
implementiert. Es handelt sich um portfolioweite Belange, die am besten auf einer
MCP-Gateway-/Host-Ebene durchgesetzt werden; das Restrisiko ist hier gering, da
der Server rein lesend ist und nur eine feste Menge vertrauenswürdiger
Open-Data-Hosts erreicht.

### SEC-014 — Tool-Allow-Listing über ein MCP-Gateway

**Status:** akzeptiertes Risiko (Portfolio-Ebene).
Eine Allow-List pro Tool gehört zum MCP-Host/-Gateway, das mehrere Server
aggregiert, nicht zu einem einzelnen Server, der ein festes, rein lesendes
Tool-Set exponiert. Sobald ein zentrales Gateway für das Portfolio eingeführt
wird, sollte das Tool-Allow-Listing dort konfiguriert werden. Bis dahin ist das
Risiko begrenzt: Jedes Tool ist rein lesend und durch die oben genannte
Egress-Allow-List eingeschränkt.

### SEC-015 — Pre-Flight-Erkennung von Tool-Poisoning

**Status:** akzeptiertes Risiko (Portfolio-Ebene).
Tool-Poisoning (bösartige Tool-Beschreibungen / Rug-Pulls) ist ein Lieferketten-
und Host-seitiges Problem. Die Tool-Definitionen dieses Servers sind
versionskontrolliert und werden aus diesem Repository ausgeliefert; es gibt keine
dynamische oder entfernte Tool-Registrierung. Die serverübergreifende
Poisoning-Erkennung bleibt eine Gateway-/Host-Verantwortung, die auf
Portfolio-Ebene verfolgt wird.

### Multi-Tenant / Streamable HTTP ohne Auth

**Status:** akzeptiertes Risiko (Einzel-User-Deployment).
Dieser Server hat keine Auth-Schicht (`auth_model: none`). Streamable HTTP ohne
Reverse-Proxy + OAuth/API-Gateway ist nur für Einzel-User-Deployments gedacht
(z. B. eine claude.ai-Browser-Session). Für Multi-Tenant-Betrieb muss ein
authentifizierender Gateway vorgeschaltet werden. Details siehe README-Abschnitt
«Cloud-Deployment».

## Re-Evaluierungs-Auslöser

Diese Akzeptanzen sollten neu bewertet werden, falls der Server jemals:

- **Schreib**-Funktionalität erhält oder beginnt, **PII** zu verarbeiten, oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann SEC-014/015 dort umsetzen).
