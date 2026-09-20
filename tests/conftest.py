"""Gemeinsame pytest-Fixtures für die Unit-Test-Suite.

Stellt Sample-CKAN-Antworten und einen respx-Helper bereit, damit
Unit-Tests offline laufen können (keine Live-Calls zu envidat.ch).
"""

from __future__ import annotations

import sys
import time
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
#
# WARUM MEHR ALS EIN VERSUCH, UND WARUM DER GRUND MITGEFÜHRT WIRD
# ---------------------------------------------------------------
# Am 11.9.2026 (Lauf 29 von live.yml, 10:01 UTC) scheiterte genau dieser Probe
# ein einziges Mal. Folge: alle 31 Live-Tests übersprungen, pytest-Exit 0, der
# Job nach 7 s rot mit `state=unknown`. Die Läufe davor und danach sind grün,
# die Quelle antwortete beim Nachmessen mit HTTP 200 — es war eine vorüber-
# gehende Netzstörung.
#
# Zwei Dinge fehlten, und beide kosten nichts:
#
#   1. Ein einziger Versuch entschied über den ganzen Lauf. Drei Versuche mit
#      kurzer Pause halten `unknown` den Fällen vor, die wirklich welche sind.
#   2. Der `except`-Block schluckte die Exception. Ob DNS, TLS, Connection
#      Refused oder Timeout — nichts davon stand im Log. Eine Sperre liess sich
#      von einer Störung nicht unterscheiden, also war der rote Lauf keine
#      Auskunft, sondern nur ein roter Lauf. Der Befund wird jetzt mitgeführt:
#      in die Skip-Meldung, ins JUnit-XML und ans Ende des Terminal-Protokolls.
#
# Drei Versuche kosten im schlimmsten Fall 3 s Pause plus 3 × 8 s Timeout —
# die Job-Grenze von 15 Minuten bleibt weit weg.

_PROBE_VERSUCHE = 3
# Pause nach dem ersten und nach dem zweiten Fehlversuch.
_PROBE_PAUSEN = (1.0, 2.0)

# Eigener Alias statt `time.sleep` direkt: Ein Test, der die Pause neutralisieren
# will, patcht diesen Namen. `monkeypatch.setattr(time, "sleep", ...)` griffe ins
# fremde Modul `time` und entschärfte das Warten im ganzen Prozess — inklusive
# allem, was pytest, httpx oder anyio selbst damit tun.
_sleep = time.sleep

# Zwei Schlüssel: `erreichbar` (bool) und `befund` (str, der Text fürs Protokoll).
_LIVE_API_PROBE: dict[str, Any] = {}


def _probe_envidat() -> tuple[bool, str]:
    """Erreichbarkeit prüfen und den Befund als Text zurückgeben.

    Gibt `(erreichbar, befund)` zurück. Der Befund benennt bei Erfolg den
    Statuscode und den Versuch, bei Misserfolg jeden Fehlversuch mit
    Exception-Typ und -Meldung.
    """
    fehlversuche: list[str] = []
    for versuch in range(1, _PROBE_VERSUCHE + 1):
        try:
            antwort = httpx.get(
                f"{ENVIDAT_API_BASE}/status_show",
                timeout=httpx.Timeout(8.0, connect=5.0),
                headers={
                    "User-Agent": "wsl-envidat-mcp-tests",
                    "Accept": "application/json",
                },
            )
        except httpx.TransportError as exc:
            # `TransportError` allein genügt: `TimeoutException`, `ConnectError`
            # und `ProxyError` sind Unterklassen davon. Beide nebeneinander zu
            # nennen liest sich wie zwei Geschwister und ist eines zu viel.
            meldung = str(exc).strip() or "(ohne Meldung)"
            fehlversuche.append(f"Versuch {versuch}: {type(exc).__name__}: {meldung}")
            if versuch < _PROBE_VERSUCHE:
                _sleep(_PROBE_PAUSEN[versuch - 1])
            continue
        # Jede HTTP-Antwort bedeutet: Server erreichbar → Live-Tests laufen lassen.
        befund = f"HTTP {antwort.status_code} bei Versuch {versuch} von {_PROBE_VERSUCHE}"
        if fehlversuche:
            befund += " — davor: " + "; ".join(fehlversuche)
        return True, befund
    return False, "; ".join(fehlversuche)


def _live_skip_grund() -> str | None:
    """`None` heisst laufen lassen; sonst der Text für `pytest.skip`.

    Eigene Funktion und keine Logik in der Fixture: So lässt sich die
    Entscheidung testen, ohne eine Fixture von Hand aufzurufen.
    """
    if "erreichbar" not in _LIVE_API_PROBE:
        erreichbar, befund = _probe_envidat()
        _LIVE_API_PROBE["erreichbar"] = erreichbar
        _LIVE_API_PROBE["befund"] = befund
    if _LIVE_API_PROBE["erreichbar"]:
        return None
    return (
        "EnviDat-API (www.envidat.ch) nicht erreichbar – Live-Tests übersprungen. "
        f"{_LIVE_API_PROBE['befund']}"
    )


@pytest.fixture(autouse=True)
def _skip_live_if_api_unreachable(request: pytest.FixtureRequest) -> None:
    """Überspringt `live`-Tests, wenn www.envidat.ch nicht erreichbar ist."""
    if request.node.get_closest_marker("live") is None:
        return
    grund = _live_skip_grund()
    if grund is not None:
        pytest.skip(grund)


def pytest_terminal_summary(terminalreporter: Any) -> None:
    """Den Befund einmal ans Ende des Protokolls schreiben.

    Die Skip-Meldung steht zwar an jedem einzelnen Test, aber `-v` kürzt sie
    auf `SKIPPED (Envi...)`. `live.yml` hängt die letzten 40 Zeilen ins Log und
    ins Issue — hier landet der Befund also dort, wo ihn jemand liest, und bei
    erreichbarer API auch die Gegenprobe dazu.
    """
    befund = _LIVE_API_PROBE.get("befund")
    if befund is None:
        return
    terminalreporter.write_sep("-", "EnviDat-Erreichbarkeit")
    terminalreporter.write_line(str(befund))


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
