"""Tests fuer den Erreichbarkeits-Probe aus conftest.py.

WOHER DIESE TESTS KOMMEN
------------------------
Lauf 29 von `live.yml`, 11.9.2026, 10:01 UTC: Der Probe gegen
`www.envidat.ch/api/action/status_show` scheiterte ein einziges Mal. Alle 31
Live-Tests wurden uebersprungen, pytest endete mit 0, der Job war nach sieben
Sekunden rot mit `state=unknown`. Die Laeufe 28, 30, 31 und 32 sind gruen, und
beim Nachmessen antwortete die Quelle dreimal mit HTTP 200 in gut einer
Sekunde. Es war eine voruebergehende Netzstoerung — nur stand das nirgends,
weil der `except`-Block die Exception verschluckte.

Zwei Zusicherungen werden hier geprueft, und beide fallen einzeln:

  1. Ein Fehlversuch beendet den Probe nicht (drei Versuche mit Pause).
  2. Was schiefging, steht im Befund — Exception-Typ und -Meldung.

Kein Netz: respx faengt den Transport ab und wirft echte httpx-Fehler.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from tests import conftest as cft

STATUS_URL = f"{cft.ENVIDAT_API_BASE}/status_show"


@pytest.fixture(autouse=True)
def _probe_cache_leeren() -> Any:
    """Der Probe-Cache ist modulweit — ohne Zuruecksetzen faerbt ein Test den naechsten.

    Nach dem Test wird der vorherige Stand wiederhergestellt: Laeuft in
    derselben Session eine echte Live-Suite, soll sie ihren Befund behalten.
    """
    vorher = dict(cft._LIVE_API_PROBE)
    cft._LIVE_API_PROBE.clear()
    yield
    cft._LIVE_API_PROBE.clear()
    cft._LIVE_API_PROBE.update(vorher)


@pytest.fixture
def pausen(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Neutralisiert das Warten und zeichnet auf, wie lange gewartet worden waere.

    Gepatcht wird der Modul-Alias `cft._sleep`, nicht `time.sleep`: Ein Griff
    ins fremde Modul entschaerfte das Warten im ganzen Prozess, auch dort, wo
    pytest, httpx oder anyio es brauchen.
    """
    aufgezeichnet: list[float] = []
    monkeypatch.setattr(cft, "_sleep", aufgezeichnet.append)
    return aufgezeichnet


class TestProbe:
    def test_drei_fehlversuche_geben_auf_und_nennen_jeden(self, pausen: list[float]) -> None:
        with respx.mock:
            route = respx.get(STATUS_URL).mock(
                side_effect=httpx.ConnectError("Name or service not known")
            )
            erreichbar, befund = cft._probe_envidat()

        assert erreichbar is False
        assert route.call_count == 3
        assert pausen == [1.0, 2.0]
        # Der Grund, weswegen diese Aenderung ueberhaupt geschrieben wurde:
        # Typ und Meldung der Exception stehen im Befund, nicht im Nichts.
        assert "ConnectError" in befund
        assert "Name or service not known" in befund
        assert "Versuch 3" in befund

    def test_zweiter_versuch_rettet_den_lauf(self, pausen: list[float]) -> None:
        """Genau der Fall vom 11.9.: ein Aussetzer, danach antwortet die Quelle."""
        with respx.mock:
            route = respx.get(STATUS_URL).mock(
                side_effect=[httpx.ConnectError("connection reset"), httpx.Response(200, json={})]
            )
            erreichbar, befund = cft._probe_envidat()

        assert erreichbar is True
        assert route.call_count == 2
        assert pausen == [1.0]
        assert "HTTP 200 bei Versuch 2" in befund
        # Der ueberstandene Fehlversuch bleibt sichtbar: Ein Lauf, der erst im
        # zweiten Anlauf durchkam, ist gruen, aber kein Schweigen wert.
        assert "connection reset" in befund

    def test_eine_fehlerantwort_ist_eine_antwort(self, pausen: list[float]) -> None:
        """5xx heisst: Der Server hat geantwortet. Kein Grund fuer einen zweiten Versuch.

        Die Unterscheidung ist dieselbe wie in CLAUDE.md: Entscheidend ist
        nicht der Statuscode, sondern ob die Quelle ueberhaupt geantwortet hat.
        Die Live-Tests duerfen an einem 503 fallen — uebersprungen werden sie
        dafuer nicht.
        """
        with respx.mock:
            route = respx.get(STATUS_URL).mock(return_value=httpx.Response(503))
            erreichbar, befund = cft._probe_envidat()

        assert erreichbar is True
        assert route.call_count == 1
        assert pausen == []
        assert "HTTP 503" in befund


class TestSkipGrund:
    def test_skip_grund_traegt_den_befund(self, pausen: list[float]) -> None:
        with respx.mock:
            respx.get(STATUS_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))
            grund = cft._live_skip_grund()

        assert grund is not None
        assert "nicht erreichbar" in grund
        assert "ConnectTimeout" in grund
        assert "timed out" in grund

    def test_erreichbare_api_wird_nicht_uebersprungen(self, pausen: list[float]) -> None:
        with respx.mock:
            respx.get(STATUS_URL).mock(return_value=httpx.Response(200, json={}))
            assert cft._live_skip_grund() is None

    def test_probe_laeuft_nur_einmal_pro_session(self, pausen: list[float]) -> None:
        """Sonst zahlte jeder der 31 Live-Tests den Probe noch einmal."""
        with respx.mock:
            route = respx.get(STATUS_URL).mock(return_value=httpx.Response(200, json={}))
            cft._live_skip_grund()
            cft._live_skip_grund()

        assert route.call_count == 1


class _Protokoll:
    """Minimaler Ersatz fuer den terminalreporter von pytest."""

    def __init__(self) -> None:
        self.zeilen: list[str] = []

    def write_sep(self, sep: str, title: str | None = None, **kw: Any) -> None:
        self.zeilen.append(str(title))

    def write_line(self, line: str, **kw: Any) -> None:
        self.zeilen.append(str(line))


class TestTerminalZusammenfassung:
    def test_befund_steht_am_ende_des_protokolls(self) -> None:
        """`-v` kuerzt die Skip-Meldung auf `SKIPPED (Envi...)`; hier steht sie ganz."""
        cft._LIVE_API_PROBE.update(
            {"erreichbar": False, "befund": "Versuch 1: ConnectError: alles kaputt"}
        )
        protokoll = _Protokoll()
        cft.pytest_terminal_summary(protokoll)

        assert any("alles kaputt" in zeile for zeile in protokoll.zeilen)

    def test_ohne_live_lauf_bleibt_das_protokoll_still(self) -> None:
        """Bei `-m "not live"` gibt es keinen Befund — und nichts zu melden."""
        protokoll = _Protokoll()
        cft.pytest_terminal_summary(protokoll)

        assert protokoll.zeilen == []
