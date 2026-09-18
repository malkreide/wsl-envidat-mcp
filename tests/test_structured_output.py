"""Spec 2026-07-28: die Tools bedienen beide Kanaele eines Tool-Resultats.

Ein Resultat hat seit dieser Revision `content` fuer den Leser und
`structuredContent` fuer die Anwendung, mit `outputSchema` als Vertrag
darueber. Dieser Server bediente nur den ersten — und das SDK fuellte den
zweiten trotzdem: eine Signatur `-> str` erzeugt ein Wrapper-Schema
`{"result": string}` und legt denselben Markdown-Block noch einmal darunter.

Gemessen an `wsl_search` gegen `tests/fixtures/package_search.json`, vor der
Umstellung: 2058 Zeichen Text, 2058 Zeichen `structuredContent.result`,
zeichengleich. Das ist schlechter als gar kein Schema. Ein `outputSchema` ist
eine Zusage; jene versprach Struktur und lieferte Prosa unter einem Schluessel
namens `result`. Wer ihr glaubte und `structuredContent` las, statt `content`
zu parsen, hatte am Ende denselben String — ueber einen Umweg, der wie eine
Datenschnittstelle aussah.

Geprueft wird durchgehend ueber eine echte `ClientSession`, nicht durch
Ruecklesen der Modelle: Ein Blick auf `SearchOutput` waere auch dann gruen,
wenn die Rueckgabe-Annotation des Tools verlorenginge und das SDK wieder
wrappte. Genau das ist der Fehler, der hier nicht mehr durchkommen soll.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from fixture_data import fixture_json
from mcp import Client
from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsl_envidat_mcp import __version__  # noqa: E402
from wsl_envidat_mcp.api_client import ENVIDAT_API_BASE  # noqa: E402
from wsl_envidat_mcp.server import mcp  # noqa: E402

# Das Schema, das das SDK aus einer `-> str`-Signatur baut. Es steht hier als
# Konstante, weil die Zusicherungen unten sich auf genau diese Form beziehen
# und `test_die_negativkontrolle_zeigt_den_wrapper` belegt, dass es sie gibt.
WRAPPER_PROPERTIES = {"result"}


def _mock_search() -> None:
    respx.get(url__startswith=f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=fixture_json("package_search"))
    )


# ─── serverInfo: die nativen Implementation-Felder ───────────────────────────


async def test_serverinfo_nennt_die_version() -> None:
    """Der Fund, der am teuersten war.

    Die Nummer wird an vier Stellen gleichgehalten — `pyproject.toml`,
    `server.json`, beide README-Badges — und `scripts/check_version_sync.py`
    haelt dieses Gate. Nur erreichte sie die eine Stelle nicht, an der ein
    Client sie liest: `serverInfo.version` stand auf `""`. Wer einen Bericht
    bekommt, dieser Server verhalte sich falsch, kann ohne sie nicht sagen,
    welcher Build gemeint ist.
    """
    async with Client(mcp) as client:
        info = client.server_info

    assert info is not None
    assert info.version == __version__, (
        f"serverInfo meldet {info.version!r}, das Paket ist {__version__!r}"
    )
    assert info.version, "eine leere Version ist keine Auskunft"


async def test_serverinfo_traegt_die_uebrigen_felder() -> None:
    """`title`, `description`, `websiteUrl` — die drei optionalen von sechs.

    Optional heisst nicht folgenlos: `title` ist der Name, den ein Client
    anzeigt, wenn er nicht den Slug zeigen will, und ohne ihn zeigt er den
    Slug.
    """
    async with Client(mcp) as client:
        info = client.server_info

    assert info is not None
    assert info.name == "wsl-envidat-mcp"
    assert info.title and "EnviDat" in info.title
    assert info.description and "WSL" in info.description
    assert info.website_url == "https://www.envidat.ch"


# ─── tools/list: Titel und Output-Schema ─────────────────────────────────────


async def test_jedes_tool_traegt_den_titel_im_nativen_feld() -> None:
    """`annotations.title` ist der Platz von vor 2026-07-28.

    Die Revision fuehrt `title` als eigenes Feld auf `Tool`; `annotations.title`
    bleibt nur als Rueckfall bestehen (SDK: `shared/metadata_utils.py`,
    `title > annotations.title > name`). Ein Client, der dem Schema folgt und
    `tool.title` liest, bekam hier `None` und zeigte den Slug.
    """
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools

    assert len(tools) == 10
    ohne = [t.name for t in tools if not t.title]
    assert not ohne, f"ohne natives `title`: {ohne}"


async def test_der_titel_steht_nicht_mehr_doppelt() -> None:
    """Zwei Stellen fuer denselben Namen sind zwei, die auseinanderlaufen."""
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools

    doppelt = [t.name for t in tools if t.annotations and t.annotations.title is not None]
    assert not doppelt, f"Titel steht noch in `annotations`: {doppelt}"


async def test_die_annotations_hints_haben_den_umzug_ueberlebt() -> None:
    """Gegenprobe zum Test davor: Der Titel sollte aus `annotations` heraus,
    die Verhaltens-Hints aber nicht mit ihm. Ohne diese Zeile waere ein
    geloeschter `annotations`-Block gruen.
    """
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools

    for tool in tools:
        assert tool.annotations is not None, tool.name
        assert tool.annotations.read_only_hint is True, tool.name
        assert tool.annotations.destructive_hint is False, tool.name


async def test_kein_tool_veroeffentlicht_mehr_das_wrapper_schema() -> None:
    """Die Kernzusage dieser Datei.

    `{"result": string}` ist kein Datenvertrag, sondern die Form, die entsteht,
    wenn niemand einen formuliert hat.
    """
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools

    gewrappt = [
        t.name
        for t in tools
        if t.output_schema and set(t.output_schema.get("properties", {})) == WRAPPER_PROPERTIES
    ]
    assert not gewrappt, f"veroeffentlichen noch `{{'result': string}}`: {gewrappt}"


async def test_jedes_tool_veroeffentlicht_die_herkunftsfelder() -> None:
    """CH-004 im maschinenlesbaren Kanal.

    Die vier Felder standen bisher nur im `response_format="json"`-Zweig — also
    nur dort, wo ein Aufrufer sie ausdruecklich anforderte. Im Schema stehen
    sie jetzt fuer jedes Tool.
    """
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools

    for tool in tools:
        assert tool.output_schema is not None, tool.name
        props = set(tool.output_schema.get("properties", {}))
        fehlend = {"source", "license", "provenance", "retrieved_at"} - props
        assert not fehlend, f"{tool.name} fehlt {sorted(fehlend)}"


# ─── Die Negativkontrolle ────────────────────────────────────────────────────


async def test_die_negativkontrolle_zeigt_den_wrapper() -> None:
    """Gleiches SDK, gleicher Client, eine Signatur `-> str`.

    Ohne diese Zeile pruefen die Zusicherungen oben nicht, dass WIR etwas tun:
    Bekaeme das SDK eines Tages einen anderen Default, blieben sie gruen und
    saehen weiter nach einer Aussage aus. Hier steht, wogegen sie sich richten
    — und der Tag, an dem dieser Test faellt, ist der Tag, an dem die anderen
    neu zu bewerten sind.
    """
    kontrolle = MCPServer("kontrolle")

    @kontrolle.tool(name="prosa")
    async def prosa() -> str:
        return "## Markdown\n\nEin Absatz."

    async with Client(kontrolle) as client:
        tool = (await client.list_tools()).tools[0]
        result = await client.call_tool("prosa", {})

    assert tool.title is None, "die Kontrolle soll gerade keinen nativen Titel haben"
    assert set(tool.output_schema["properties"]) == WRAPPER_PROPERTIES
    assert result.structured_content == {"result": result.content[0].text}, (
        "die Kontrolle soll den Text verdoppeln — genau das war der Ausgangszustand"
    )


# ─── tools/call: was tatsaechlich ankommt ────────────────────────────────────


@respx.mock
async def test_die_suche_liefert_daten_statt_einer_textkopie() -> None:
    """Der Unterschied, um den es geht, an der Antwort selbst."""
    _mock_search()
    erwartet = fixture_json("package_search")["result"]

    async with Client(mcp) as client:
        result = await client.call_tool(
            "wsl_search", {"params": {"query": "snow avalanche", "limit": 2}}
        )

    text = result.content[0].text
    daten = result.structured_content
    assert daten is not None

    assert daten != {"result": text}, "das ist wieder die Textkopie"
    assert daten["total_found"] == erwartet["count"]
    assert daten["shown"] == len(daten["datasets"]) == 2
    assert daten["datasets"][0]["name"] == erwartet["results"][0]["name"]
    assert daten["datasets"][0]["url"].startswith("https://www.envidat.ch/dataset/")
    assert daten["provenance"] == "live_api"
    # Der Textkanal bleibt, was er war: lesbares Markdown, nicht JSON.
    assert text.startswith("## ")
    assert erwartet["results"][0]["title"][:24] in text


@respx.mock
async def test_text_und_struktur_stammen_aus_einem_aufbau(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zwei Aufbauten derselben Nutzlast waeren zwei Wahrheiten.

    Diese Zusicherung stand hier schon einmal — ohne die Uhr unten, und damit
    wertlos. Die Gegenprobe (Nutzlast absichtlich zweimal bauen) liess sie
    gruen: Beide Aufbauten fielen in dieselbe Sekunde, und eine Zusicherung
    ueber echte Zeit laesst sich mit echter Zeit nicht widerlegen.

    Die Uhr hier rueckt bei JEDEM Abruf eine Sekunde vor. Damit heisst
    «beide Kanaele nennen denselben Zeitpunkt» genau noch eins: Die Nutzlast
    wurde ein einziges Mal gebaut. Wird sie verdoppelt, faellt der Test.

    Ersetzt wird der Modul-Alias `_utc_now`, nicht `datetime`: Ein
    `monkeypatch.setattr(server.datetime, ...)` griffe ins fremde Modul und
    entschaerfte es im ganzen Prozess.
    """
    from wsl_envidat_mcp import server

    ticks = iter(range(1, 100))
    monkeypatch.setattr(server, "_utc_now", lambda: f"2026-07-28T00:00:{next(ticks):02d}+00:00")

    _mock_search()

    async with Client(mcp) as client:
        result = await client.call_tool(
            "wsl_search",
            {"params": {"query": "forest", "response_format": "json"}},
        )

    aus_text = json.loads(result.content[0].text)
    assert result.structured_content == aus_text
    assert aus_text["retrieved_at"] == "2026-07-28T00:00:01+00:00", (
        "die zweite Sekunde bedeutet: die Nutzlast wurde ein zweites Mal gebaut"
    )


def test_die_uhr_des_tests_darueber_rueckt_wirklich_vor() -> None:
    """Gegenprobe zur Gegenprobe.

    Eine Uhr, die stehenbleibt, machte den Test oben wieder zu dem, was er
    vorher war: gruen, egal wie oft gebaut wird. Hier steht, dass sie laeuft.
    """
    from wsl_envidat_mcp import server

    assert server._utc_now() is not None
    ticks = iter(range(1, 4))
    uhr = lambda: f"2026-07-28T00:00:{next(ticks):02d}+00:00"  # noqa: E731
    assert uhr() != uhr()


@respx.mock
async def test_die_tag_vorschlaege_stehen_auch_als_liste() -> None:
    """ARCH-003 im zweiten Kanal: im Text Prosa, hier eine Liste.

    Ein Aufrufer musste den Hinweis bisher aus einem Satz herausloesen.
    """
    respx.get(url__startswith=f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(
            200, json={"success": True, "result": {"count": 0, "results": []}}
        )
    )
    respx.get(url__startswith=f"{ENVIDAT_API_BASE}/tag_list").mock(
        return_value=httpx.Response(
            200, json={"success": True, "result": ["xyzzy-test", "xyzzy-data"]}
        )
    )

    async with Client(mcp) as client:
        result = await client.call_tool("wsl_search", {"params": {"query": "xyzzy"}})

    daten = result.structured_content
    assert daten is not None
    assert daten["total_found"] == 0
    assert daten["datasets"] == []
    assert "xyzzy-test" in daten["suggested_tags"]
    assert "xyzzy-test" in result.content[0].text


@respx.mock
async def test_der_json_zweig_gibt_weiterhin_das_rohe_paket() -> None:
    """Die Zusage, dass niemand Daten verliert.

    `wsl_get_dataset(response_format="json")` lieferte im Textkanal das rohe
    CKAN-Paket mit allen Feldern. Es auf die kuratierten zu verengen, haette
    ein Schema gewonnen und Daten weggenommen — deshalb traegt der Textkanal
    weiter das Rohe und `structuredContent` das Kuratierte.
    """
    paket = fixture_json("package_show")["result"]
    respx.get(url__startswith=f"{ENVIDAT_API_BASE}/package_show").mock(
        return_value=httpx.Response(200, json=fixture_json("package_show"))
    )

    async with Client(mcp) as client:
        result = await client.call_tool(
            "wsl_get_dataset",
            {"params": {"id_or_slug": paket["name"], "response_format": "json"}},
        )

    roh = json.loads(result.content[0].text)
    assert set(roh) == set(paket), "der Rohzweig hat Felder verloren"

    daten = result.structured_content
    assert daten is not None
    assert daten["name"] == paket["name"]
    assert len(daten["resources"]) == len(paket["resources"])


@pytest.mark.parametrize("groesse", ["12 KB", None, "4096"])
def test_unlesbare_groessenangaben_brechen_den_aufruf_nicht(groesse: Any) -> None:
    """CKAN fuehrt `size` mal als Zahl, mal als Zeichenkette, mal gar nicht.

    Ohne die Umwandlung entschiede die Schreibweise der Quelle darueber, ob der
    Aufruf gelingt: Ein `"12 KB"` liesse die Modellvalidierung den ganzen
    Datensatz verwerfen — ein kosmetischer Mangel der Quelle wuerde zum Ausfall
    des Werkzeugs.
    """
    from wsl_envidat_mcp.server import _dataset_detail_payload

    payload = _dataset_detail_payload(
        {"name": "x", "resources": [{"name": "d.csv", "size": groesse}]}
    )
    assert len(payload.resources) == 1
    assert payload.resources[0].size == (4096 if groesse == "4096" else None)
