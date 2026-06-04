# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`wsl-envidat-mcp` was hardened against the internal MCP best-practice audit
catalogue (`mcp-audit-skill` v1.0.0). This document summarises the security
posture and records the **accepted-risk** decisions for controls that are
deliberately handled at the portfolio/gateway layer rather than inside this
single server.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

This is a **read-only**, **no-PII**, **public-open-data** MCP server. All 10
tools only query the official EnviDat CKAN API (WSL — Swiss Federal Research
Institute for Forest, Snow and Landscape) at `envidat.ch`. Hardening already in
place:

| Area | Control |
|---|---|
| Egress | HTTPS-enforced allow-list to fixed EnviDat hosts only (`ALLOWED_HOSTS` in `api_client.py`, SEC-021) |
| Redirects | `follow_redirects=False` closes the cross-origin redirect-hijack window (SEC-005/SEC-021) |
| TLS | Certificate verification on by default (`httpx` default) |
| Binding | Network transports default to `127.0.0.1`; `0.0.0.0` only via explicit `MCP_HOST` inside a container (SEC-016) |
| Input | Pydantic v2 validation at all tool boundaries (SEC-018) |
| Secrets | None required — non-secret env-vars only, `.gitignore` guards `.env`, no hardcoded secrets (ARCH-005/SEC-013) |
| Errors | Upstream bodies logged to stderr, never forwarded to the model (OBS-002) |
| Stdout | Reserved for the JSON-RPC stream; structured logging pinned to stderr (OBS-003/OBS-004) |
| Container | Hardened multi-stage image, runs as non-root (`uid=1000`), no build tools in the runtime layer |

See `audits/` for the underlying audit reports (latest run: 2026-05-28,
31/32 checks pass, 0 critical/high) and `CHANGELOG.md` for the hardening history.

## Accepted risks (portfolio-level controls)

The following audit checks are **not** implemented inside this server by design.
They are portfolio-wide concerns best enforced at an MCP gateway / host layer,
and the residual risk here is low because the server is read-only and only
reaches a fixed set of trusted public-data hosts.

### SEC-014 — Tool allow-listing via an MCP gateway

**Status:** accepted risk (portfolio-level).
A per-tool allow-list belongs to the MCP host/gateway that aggregates multiple
servers, not to an individual server that exposes a fixed, read-only tool set.
If/when a central gateway is introduced for the portfolio, tool allow-listing
should be configured there. Until then, the risk is bounded: every tool is
read-only and constrained by the egress allow-list above.

### SEC-015 — Pre-flight tool-poisoning detection

**Status:** accepted risk (portfolio-level).
Tool-poisoning (malicious tool descriptions / rug-pulls) is a supply-chain and
host-side concern. This server's tool definitions are version-controlled and
shipped from this repository; there is no dynamic or remote tool registration.
Cross-server poisoning detection remains a gateway/host responsibility tracked
at the portfolio level.

### Multi-tenant / unauthenticated Streamable HTTP

**Status:** accepted risk (single-user deployment).
This server has no auth layer (`auth_model: none`). Streamable HTTP without a
reverse-proxy + OAuth/API-Gateway is intended only for single-user deployments
(e.g. one user's claude.ai browser session). For multi-tenant use, front the
server with an authenticating gateway. See the README "Cloud Deployment"
section for details.

## Re-evaluation triggers

These acceptances should be revisited if the server ever:

- gains **write** capability or starts processing **PII**, or
- registers tools **dynamically** / from remote sources, or
- is aggregated behind a shared MCP gateway (then implement SEC-014/015 there).
