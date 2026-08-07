"""Gemeinsame pytest-Fixtures für die Unit-Test-Suite.

Stellt Sample-CKAN-Antworten und einen respx-Helper bereit, damit
Unit-Tests offline laufen können (keine Live-Calls zu envidat.ch).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

# src/ ins sys.path aufnehmen für ungebundene Imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# Das eigene Verzeichnis dazu: Dieser conftest wird geladen, bevor pytest
# tests/ auf den Pfad legt, und `fixture_data` liegt daneben.
sys.path.insert(0, str(Path(__file__).parent))

from fixture_data import fixture_json  # noqa: E402

from wsl_envidat_mcp.api_client import ENVIDAT_API_BASE  # noqa: E402

# ─── Live-API-Erreichbarkeit ────────────────────────────────────────────────────
# Live-Tests hängen sonst pro Request bis zum vollen REQUEST_TIMEOUT (30 s),
# wenn www.envidat.ch nicht erreichbar ist (Ausfall, IP-Blockade des CI-Runners,
# Netzwerk). Bei ~30 Tests mit je mehreren Calls sprengt das die 10-Minuten-
# Job-Grenze. Wir prüfen die Erreichbarkeit deshalb EINMAL pro Session mit
# kurzem Timeout und überspringen alle Live-Tests sauber, wenn die API nicht
# antwortet. Echte API-Regressionen schlagen weiterhin fehl, solange die API
# erreichbar ist (jede HTTP-Antwort – auch 4xx/5xx – gilt als erreichbar).

_LIVE_API_PROBE: dict[str, bool] = {}


def _envidat_reachable() -> bool:
    """Einmaliger, schneller Reachability-Probe gegen die EnviDat-API."""
    try:
        httpx.get(
            f"{ENVIDAT_API_BASE}/status_show",
            timeout=httpx.Timeout(8.0, connect=5.0),
            headers={
                "User-Agent": "wsl-envidat-mcp-tests",
                "Accept": "application/json",
            },
        )
        # Jede HTTP-Antwort bedeutet: Server erreichbar → Live-Tests laufen lassen.
        return True
    except (httpx.TimeoutException, httpx.TransportError):
        return False


@pytest.fixture(autouse=True)
def _skip_live_if_api_unreachable(request: pytest.FixtureRequest) -> None:
    """Überspringt `live`-Tests, wenn www.envidat.ch nicht erreichbar ist."""
    if request.node.get_closest_marker("live") is None:
        return
    if "reachable" not in _LIVE_API_PROBE:
        _LIVE_API_PROBE["reachable"] = _envidat_reachable()
    if not _LIVE_API_PROBE["reachable"]:
        pytest.skip("EnviDat-API (www.envidat.ch) nicht erreichbar – Live-Tests übersprungen")


@pytest.fixture
def sample_dataset() -> dict[str, Any]:
    """Ein echter, aufgezeichneter CKAN-Package-Eintrag.

    Die handgeschriebene Vorgaengerin trug 9 Felder — die Quelle liefert 42.
    Ihre `extras` (`authors`, `publication_year`) gibt es dort nicht, und ihre
    Tags waren kleingeschrieben, waehrend EnviDat sie in GROSSBUCHSTABEN
    fuehrt. Herkunft und Datum in tests/fixtures/PROVENANCE.md.
    """
    return fixture_json("package_show")["result"]


@pytest.fixture
def sample_search_response() -> dict[str, Any]:
    """Eine aufgezeichnete CKAN package_search-Antwort.

    `count` ist der echte Gesamtbestand, nicht die Zahl der enthaltenen
    Datensaetze — eine Fixture, die den Bestand kleiner behauptet, als er ist,
    waere genau der Fehler, gegen den das Aufzeichnen angeht.
    """
    return fixture_json("package_search")


@pytest.fixture
def sample_orgs_response() -> dict[str, Any]:
    """Die aufgezeichnete organization_list-Antwort.

    Die Vorgaengerin nannte «wsl» und «slf» — beide gibt es in EnviDat nicht;
    `organization_show?id=slf` antwortet mit 404. Die echten Namen sind Slugs
    wie `avalanche-formation`.
    """
    return fixture_json("organization_list")


@pytest.fixture
def sample_org_show_response() -> dict[str, Any]:
    """Die aufgezeichnete organization_show-Antwort einer echten Organisation."""
    return fixture_json("organization_show")


@pytest.fixture
def sample_tag_list_response() -> dict[str, Any]:
    """Die aufgezeichnete tag_list-Antwort, in der Schreibweise der Quelle."""
    return fixture_json("tag_list")
