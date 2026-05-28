# syntax=docker/dockerfile:1.7
#
# Multi-Stage Build für wsl-envidat-mcp (Audit-Finding SEC-007).
# Ziel: minimaler, non-root Container für Cloud-Deployment.

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

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
FROM python:3.11-slim

# Non-root User (SEC-007)
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin mcp

# Site-Packages aus dem Builder kopieren
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

USER mcp
WORKDIR /home/mcp

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

# OCI-Metadaten (org.opencontainers.image.*) — werden im Workflow überschrieben
LABEL org.opencontainers.image.source="https://github.com/malkreide/wsl-envidat-mcp" \
      org.opencontainers.image.title="wsl-envidat-mcp" \
      org.opencontainers.image.description="MCP server for WSL/EnviDat Swiss environmental research data" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["python", "-m", "wsl_envidat_mcp.server"]
