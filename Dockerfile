# syntax=docker/dockerfile:1.7
#
# Multi-Stage Build für wsl-envidat-mcp (Audit-Finding SEC-007).
# Ziel: minimaler, non-root Container für Cloud-Deployment.

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Build-Time-Tools, danach gepurged
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

# Installation in einen separaten Pfad, der dann in das Runtime-Image kopiert wird
RUN pip install --no-cache-dir --target=/install .

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.13-slim

# Non-root User (SEC-007)
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin mcp

# Die Abhaengigkeiten liegen unter einem eigenen Pfad und kommen ueber
# PYTHONPATH dazu. Vorher stand hier `/usr/local/lib/python3.11/site-packages`
# — die Minor-Version war in den Pfad geschrieben und musste zu `FROM` passen.
# Am 2026-09-20 hob ein Dependabot-PR das Basis-Image von 3.11 auf 3.14 und
# liess den Pfad stehen: Die Abhaengigkeiten landeten in einem Verzeichnis, in
# das der Interpreter nie schaut. `docker build` meldete nichts, weil `COPY`
# den Pfad einfach anlegt — das Image ging als v0.3.0 raus und konnte nicht
# starten.
#
# Der Pfad traegt jetzt keine Version mehr. Das macht das Image NICHT
# versionsunabhaengig: `--target` installiert ABI-gebundene Binaerteile
# (`_cffi_backend.cpython-313-*.so`), beide Stufen muessen dieselbe
# Minor-Version fahren. Dagegen schuetzt nicht der Pfad, sondern der
# Smoke-Test weiter unten.
COPY --from=builder /install /opt/deps

USER mcp
WORKDIR /home/mcp

ENV PYTHONPATH=/opt/deps \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    PORT=8000

# Smoke-Test zur Build-Zeit, derselbe Import wie das Gate in `ci.yml`.
# Er ist der eigentliche Schutz: Ein Basis-Image-Bump, der die Abhaengigkeiten
# unerreichbar macht, faellt hier auf, statt als lauffaehig aussehendes Image
# ausgeliefert zu werden. Ohne ihn baut ein kaputtes Image gruen durch.
RUN python -c "from wsl_envidat_mcp.server import mcp; print('Import OK')"

EXPOSE 8000

# OCI-Metadaten (org.opencontainers.image.*) — werden im Workflow überschrieben
LABEL org.opencontainers.image.source="https://github.com/malkreide/wsl-envidat-mcp" \
      org.opencontainers.image.title="wsl-envidat-mcp" \
      org.opencontainers.image.description="MCP server for WSL/EnviDat Swiss environmental research data" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["python", "-m", "wsl_envidat_mcp.server"]
