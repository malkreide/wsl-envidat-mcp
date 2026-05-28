"""Unit-Tests für die Security-Hardening aus Audit Batch 1.

Deckt ab:
- SEC-021: Egress-Allow-List (ALLOWED_HOSTS, assert_host_allowed)
- SEC-005: keine Cross-Origin-Redirects (follow_redirects=False)
- SEC-016: MCP_HOST-Default ist 127.0.0.1

Keine Live-Calls — alle HTTP-Aufrufe sind via respx gemockt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
import respx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsl_envidat_mcp.api_client import (  # noqa: E402
    ALLOWED_HOSTS,
    ENVIDAT_API_BASE,
    assert_host_allowed,
    ckan_package_search,
)


# ─── SEC-021: Egress-Allow-List ──────────────────────────────────────────────


def test_allowed_hosts_contains_envidat() -> None:
    assert "www.envidat.ch" in ALLOWED_HOSTS
    assert "envidat.ch" in ALLOWED_HOSTS


def test_assert_host_allowed_passes_for_envidat() -> None:
    assert_host_allowed("https://www.envidat.ch/api/action/package_search")
    assert_host_allowed("https://envidat.ch/dataset/foo")


@pytest.mark.parametrize(
    "url",
    [
        "https://attacker.example.com/exfiltrate",
        "http://169.254.169.254/latest/meta-data/",
        "https://envidat.ch.attacker.com/phish",
        "https://EnviDat.attacker.com/",
    ],
)
def test_assert_host_allowed_rejects_foreign_hosts(url: str) -> None:
    with pytest.raises(PermissionError, match="egress allow-list"):
        assert_host_allowed(url)


# ─── SEC-005: keine Cross-Origin-Redirects ───────────────────────────────────


@respx.mock
async def test_redirect_does_not_silently_follow_cross_origin() -> None:
    """Wenn envidat.ch einen 302 zu attacker.com ausliefert, darf der
    Client NICHT folgen. Mit follow_redirects=False führt das zu einem
    HTTPStatusError beim raise_for_status."""
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(
            302,
            headers={"location": "https://attacker.example.com/exfiltrate"},
        )
    )

    with pytest.raises(httpx.HTTPStatusError):
        await ckan_package_search(query="test")


# ─── Happy Path: gemockte EnviDat-Antwort ────────────────────────────────────


@respx.mock
async def test_ckan_package_search_happy_path() -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "count": 2,
                    "results": [
                        {"name": "ds-1", "title": "Dataset 1"},
                        {"name": "ds-2", "title": "Dataset 2"},
                    ],
                },
            },
        )
    )

    result = await ckan_package_search(query="snow")
    assert result["count"] == 2
    assert len(result["results"]) == 2


# ─── SEC-016: MCP_HOST-Default ───────────────────────────────────────────────


def test_main_defaults_to_127_0_0_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bei MCP_TRANSPORT=streamable-http ohne MCP_HOST muss host=127.0.0.1
    sein. Wir patchen mcp.run, um den Server nicht wirklich zu starten."""
    from wsl_envidat_mcp import server

    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("PORT", "9876")

    called_with: dict[str, object] = {}

    def fake_run(transport: str) -> None:
        called_with["transport"] = transport
        called_with["host"] = server.mcp.settings.host
        called_with["port"] = server.mcp.settings.port

    monkeypatch.setattr(server.mcp, "run", fake_run)
    server.main()

    assert called_with["transport"] == "streamable-http"
    assert called_with["host"] == "127.0.0.1"
    assert called_with["port"] == 9876


def test_main_accepts_legacy_underscore_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backward-Kompat: MCP_TRANSPORT=streamable_http (underscore) wird
    auf den kanonischen Wert streamable-http normalisiert."""
    from wsl_envidat_mcp import server

    monkeypatch.setenv("MCP_TRANSPORT", "streamable_http")
    monkeypatch.setenv("PORT", "8000")

    called_with: dict[str, object] = {}
    monkeypatch.setattr(
        server.mcp,
        "run",
        lambda transport: called_with.update(transport=transport),
    )
    server.main()
    assert called_with["transport"] == "streamable-http"
