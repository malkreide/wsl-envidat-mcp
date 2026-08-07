"""Die CKAN-Hülle wird bestätigt, nicht angenommen (FID-006).

`_parse_response` schrieb `data.get("result", {})`. Das macht aus **jeder**
Strukturänderung der Quelle ein gültiges leeres Ergebnis: Der Tool-Call gelingt,
die Antwort ist leer, und für das Modell ist das nicht von «EnviDat kennt diesen
Datensatz nicht» zu unterscheiden. Ein Ausfall, der wie eine Antwort aussieht.

Der Portfolio-Durchlauf am 2026-08-07 fand acht Server, die mit CKAN sprechen.
Alle acht prüfen brav das `success`-Envelope — und sieben von ihnen holen
`result` danach mit einem stillen Default. Nur `zurich-opendata-mcp` schrieb
`data["result"]` und scheiterte laut. Dieser Test hält die Reparatur fest.

Jeder Testfall hat seine Gegenprobe: Die alte Fassung liefert überall `{}`
zurück, und die Assertions unten sind genau die, die das aufdecken.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsl_envidat_mcp.api_client import (  # noqa: E402
    ENVIDAT_API_BASE,
    UpstreamSchemaError,
    ckan_organization_list,
    ckan_package_search,
    ckan_tag_list,
    handle_api_error,
)


def _mock(action: str, payload: Any) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/{action}").mock(return_value=httpx.Response(200, json=payload))


# --- Der Fund: `result` fehlt ------------------------------------------------


@respx.mock
async def test_a_missing_result_raises_instead_of_returning_nothing():
    """Die Kernzusage. Vorher: `{}` und ein zufriedener Aufrufer."""
    _mock("package_search", {"success": True, "help": "https://envidat.ch/api/3/"})
    with pytest.raises(UpstreamSchemaError):
        await ckan_package_search(query="schnee")


@respx.mock
async def test_the_message_names_the_keys_that_are_actually_there():
    """Ohne die vorhandenen Schlüssel ist der nächste Schritt Raten.

    Die Antwort enthält sie — sie nicht auszugeben, ist eine Entscheidung
    gegen die Diagnose.
    """
    _mock("package_search", {"success": True, "help": "…", "payload": {}})
    with pytest.raises(UpstreamSchemaError) as excinfo:
        await ckan_package_search(query="schnee")
    message = str(excinfo.value)
    assert "'help'" in message and "'payload'" in message, message
    assert "package_search" in message, "die Aktion gehört in die Meldung"


@respx.mock
async def test_the_message_says_this_is_not_an_empty_result():
    """Der Satz, der den Leser vom Leermengen-Hinweis wegführt."""
    _mock("package_search", {"success": True})
    with pytest.raises(UpstreamSchemaError) as excinfo:
        await ckan_package_search(query="schnee")
    assert "keine Leermenge" in str(excinfo.value)


# --- Die Hülle ist gar keine Hülle -------------------------------------------


@respx.mock
async def test_a_bare_list_instead_of_the_envelope_raises():
    """Vorher ein `AttributeError` aus `.get` — richtig laut, falsch benannt."""
    _mock("package_search", [{"name": "irgendwas"}])
    with pytest.raises(UpstreamSchemaError) as excinfo:
        await ckan_package_search(query="schnee")
    assert "list" in str(excinfo.value)


# --- Was weiterhin durchgehen muss -------------------------------------------


@respx.mock
async def test_a_genuinely_empty_search_is_still_a_normal_result():
    """Die Gegenrichtung, und sie ist die wichtigere Hälfte.

    Ein Wächter, der die echte Leermenge mitfängt, wird nach dem zweiten
    Fehlalarm abgeschaltet. `count: 0` ist eine **Aussage der Quelle** und kein
    Strukturfehler — `results` ist da, nur leer.
    """
    _mock("package_search", {"success": True, "result": {"count": 0, "results": []}})
    out = await ckan_package_search(query="gibtesnicht")
    assert out == {"count": 0, "results": []}


@respx.mock
async def test_a_list_result_survives_the_check():
    """`organization_list` und `tag_list` liefern eine Liste, kein Objekt.

    Der alte Default `{}` war für diese beiden nicht einmal vom richtigen Typ:
    Eine Strukturänderung hätte hier ein `dict` geliefert, wo der Aufrufer eine
    Liste erwartet — ein zweiter Fehler, den derselbe Default erzeugt hat.
    """
    _mock("organization_list", {"success": True, "result": ["wsl", "slf"]})
    assert await ckan_organization_list() == ["wsl", "slf"]

    _mock("tag_list", {"success": True, "result": []})
    assert await ckan_tag_list() == []


@respx.mock
async def test_a_real_ckan_error_stays_a_ckan_error():
    """Die Quelle hat geantwortet und Nein gesagt — das ist keine Formänderung.

    Die beiden auseinanderzuhalten ist der Zweck des eigenen Typs: Bei einem
    CKAN-Fehler ist die Behebung die Anfrage, hier ist sie der Leser.
    """
    _mock("package_search", {"success": False, "error": {"message": "Not authorized"}})
    with pytest.raises(ValueError) as excinfo:
        await ckan_package_search(query="schnee")
    assert not isinstance(excinfo.value, UpstreamSchemaError)
    assert "Not authorized" in str(excinfo.value)


# --- Die Fehlermeldung erreicht den Aufrufer ---------------------------------


def test_handle_api_error_still_formats_the_new_type():
    """`UpstreamSchemaError` erbt von `ValueError`, damit genau das gilt.

    Als eigenständige `Exception` wäre sie in den Zweig «Unerwarteter Fehler»
    gefallen — die Meldung, die einem Nutzer am wenigsten sagt.
    """
    text = handle_api_error(UpstreamSchemaError("Antwort ohne 'result'."), "suche")
    assert "Unerwarteter Fehler" not in text
    assert "Antwort ohne 'result'." in text
