"""Gateway-Fehler der Quelle: wiederholen, und dem Modell kein HTML zeigen.

WOHER DIESE TESTS KOMMEN
------------------------
Die geplante Live-Suite war am 14.11.2026 (Lauf 93) und am 19.11.2026 (Lauf 98)
rot: 19 bzw. 10 von 31 Tests mit HTTP 502 von www.envidat.ch. Die Laeufe davor
und danach sind gruen; beim Nachmessen am 22.11. antworteten dieselben URLs
20-mal mit HTTP 200. Am 19.11. fiel `package_search` in einem Test und lief in
anderen derselben Minute durch — die Quelle flackerte, der Vertrag stand.

Zwei Maengel im Server selbst hat der Vorfall sichtbar gemacht:

  1. Kein zweiter Versuch, obwohl jeder Aufruf ein lesendes GET ist.
  2. Die Fehlermeldung ans Modell trug die ersten 200 Zeichen des
     Antwortkoerpers — bei einem 502 reines HTML-Geruest ohne ein Wort
     Auskunft. Genau das stand danach im Issue.

DIE 502-SEITE IST AUFGEZEICHNET, NICHT AUSGEDACHT
-------------------------------------------------
`ENVIDAT_502_ANFANG` ist der Anfang der echten Antwort, woertlich aus dem
Protokoll von Lauf 98 (19.11.2026). Laenger ist er nicht erhalten, weil der
alte Code selbst nach 200 Zeichen abschnitt. Der Content-Type ist nicht
aufgezeichnet; der Test setzt deshalb keinen und prueft damit den schwereren
Fall, in dem nur der Koerper verraet, dass es HTML ist.

Kein Netz: respx faengt den Transport ab.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError

from wsl_envidat_mcp import api_client
from wsl_envidat_mcp.api_client import (
    ENVIDAT_API_BASE,
    ckan_package_show,
    ckan_status_show,
    handle_api_error,
)
from wsl_envidat_mcp.server import GetDatasetInput, wsl_get_dataset

# Aufgezeichnet: Protokoll von live.yml, Lauf 98, 19.11.2026, 14:45 UTC.
ENVIDAT_502_ANFANG = (
    "<!DOCTYPE html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '    <meta charset="UTF-8">\n'
    '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    "    <title>Error</title>\n"
    "</head>\n"
    "<body>\n"
    "    <h1>Oops! Some"
)

STATUS_URL = f"{ENVIDAT_API_BASE}/status_show"
SHOW_URL = f"{ENVIDAT_API_BASE}/package_show"


def _ok(payload: Any) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": payload})


def _status_error(response: httpx.Response) -> httpx.HTTPStatusError:
    """Ein HTTPStatusError, wie `raise_for_status` ihn wirft."""
    response.request = httpx.Request("GET", STATUS_URL)
    return httpx.HTTPStatusError("boom", request=response.request, response=response)


@pytest.fixture
def pausen(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Neutralisiert das Warten und zeichnet auf, wie lange gewartet worden waere.

    Gepatcht wird der Modul-Alias `api_client._sleep`, nicht `asyncio.sleep`:
    Ein Griff ins fremde Modul entschaerfte das Warten auch in der Event-Loop.
    """
    aufgezeichnet: list[float] = []

    async def _merken(sekunden: float) -> None:
        aufgezeichnet.append(sekunden)

    monkeypatch.setattr(api_client, "_sleep", _merken)
    return aufgezeichnet


# ─── 1. Wiederholung ─────────────────────────────────────────────────────────


class TestWiederholung:
    @respx.mock
    async def test_ein_502_wird_vom_zweiten_versuch_aufgefangen(self, pausen: list[float]) -> None:
        """Der Fall vom 19.11.: ein Aussetzer, Sekunden spaeter antwortet die Quelle."""
        route = respx.get(STATUS_URL).mock(
            side_effect=[httpx.Response(502, text=ENVIDAT_502_ANFANG), _ok({"site_title": "x"})]
        )

        result = await ckan_status_show()

        assert result == {"site_title": "x"}
        assert route.call_count == 2
        assert pausen == [0.5]

    @pytest.mark.parametrize("code", [503, 504])
    @respx.mock
    async def test_503_und_504_werden_ebenso_wiederholt(
        self, code: int, pausen: list[float]
    ) -> None:
        route = respx.get(STATUS_URL).mock(side_effect=[httpx.Response(code), _ok({})])

        await ckan_status_show()

        assert route.call_count == 2

    @respx.mock
    async def test_ein_bleibender_502_gibt_nach_drei_versuchen_auf(
        self, pausen: list[float]
    ) -> None:
        route = respx.get(STATUS_URL).mock(
            return_value=httpx.Response(502, text=ENVIDAT_502_ANFANG)
        )

        with pytest.raises(httpx.HTTPStatusError) as exc:
            await ckan_status_show()

        assert exc.value.response.status_code == 502
        assert route.call_count == 3
        assert pausen == [0.5, 1.0]

    @respx.mock
    async def test_ein_500_wird_nicht_wiederholt(self, pausen: list[float]) -> None:
        """Ein 500 kann an der Anfrage haengen und kehrt dann jedes Mal zurueck."""
        route = respx.get(STATUS_URL).mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await ckan_status_show()

        assert route.call_count == 1
        assert pausen == []

    @respx.mock
    async def test_ein_404_wird_nicht_wiederholt(self, pausen: list[float]) -> None:
        """Eine deterministische Absage bekommt keinen zweiten Versuch."""
        route = respx.get(SHOW_URL).mock(return_value=httpx.Response(404, text="not found"))

        with pytest.raises(httpx.HTTPStatusError):
            await ckan_package_show("gibt-es-nicht")

        assert route.call_count == 1
        assert pausen == []


# ─── 2. Die Meldung ans Modell ──────────────────────────────────────────────


class TestMeldung:
    def test_ein_502_nennt_den_status_und_kein_html(self) -> None:
        text = handle_api_error(
            _status_error(httpx.Response(502, text=ENVIDAT_502_ANFANG)), "wsl_search"
        )

        assert "HTTP 502 Bad Gateway" in text
        assert "Störung" in text
        assert "späterer Versuch" in text
        assert "<" not in text
        assert "DOCTYPE" not in text

    def test_ein_500_mit_html_nennt_den_status_ohne_wiederholungsrat(self) -> None:
        """Kein Rat zum erneuten Versuch: Ein 500 kann deterministisch sein."""
        text = handle_api_error(
            _status_error(httpx.Response(500, text=ENVIDAT_502_ANFANG)), "wsl_search"
        )

        assert "HTTP 500 Internal Server Error" in text
        assert "<" not in text
        assert "späterer Versuch" not in text

    def test_html_wird_auch_am_content_type_erkannt(self) -> None:
        """Ein Gateway kann HTML schicken, das nicht mit `<` beginnt."""
        antwort = httpx.Response(
            500,
            text="Service kaputt, bitte Admin rufen",
            headers={"content-type": "text/html; charset=utf-8"},
        )

        text = handle_api_error(_status_error(antwort), "wsl_search")

        assert "Admin rufen" not in text

    def test_ein_json_fehlerkoerper_von_ckan_bleibt_stehen(self) -> None:
        """Ein CKAN-Fehler ist eine Auskunft der Quelle — nur HTML faellt weg."""
        antwort = httpx.Response(
            409,
            json={"success": False, "error": {"q": ["Ungueltige Solr-Syntax"]}},
        )

        text = handle_api_error(_status_error(antwort), "wsl_search")

        assert "HTTP 409" in text
        assert "Ungueltige Solr-Syntax" in text


# ─── 3. Ende zu Ende: was das Modell als ToolError sieht ─────────────────────


@respx.mock
async def test_das_tool_meldet_einen_bleibenden_502_ohne_html(pausen: list[float]) -> None:
    """Genau die Zeile, die am 14. und 19.11. ins Issue ging — jetzt lesbar."""
    respx.get(SHOW_URL).mock(return_value=httpx.Response(502, text=ENVIDAT_502_ANFANG))

    with pytest.raises(ToolError) as exc:
        await wsl_get_dataset(GetDatasetInput(id_or_slug="snow-depth-mapping"))

    meldung = str(exc.value)
    assert "HTTP 502" in meldung
    assert "<" not in meldung
