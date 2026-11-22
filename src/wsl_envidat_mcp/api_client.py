"""HTTP-Client für die EnviDat CKAN API.

WSL – Eidg. Forschungsanstalt für Wald, Schnee und Landschaft.

API-Basis: https://www.envidat.ch/api/action/
Dokumentation: https://docs.ckan.org/en/latest/api/index.html
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from . import __version__

logger = logging.getLogger(__name__)

# ─── Konstanten ───────────────────────────────────────────────────────────────

ENVIDAT_API_BASE = "https://www.envidat.ch/api/action"
ENVIDAT_PORTAL = "https://www.envidat.ch"
REQUEST_TIMEOUT = 30.0  # Sekunden

# Gateway-Fehler, die eine Wiederholung rechtfertigen (RES-001).
#
# Am 14.11. und 19.11.2026 war die geplante Live-Suite rot: 19 bzw. 10 von 31
# Tests mit HTTP 502 von www.envidat.ch. Am 19.11. fiel `package_search` in einem
# Test und lief im naechsten durch, Sekunden spaeter, mit denselben Parametern —
# die Quelle flackerte. Die Nutzer des Servers trifft dasselbe, nur ohne Issue.
#
# 500 steht bewusst NICHT in dieser Menge. Ein 500 kann an der Anfrage haengen
# (eine Solr-Query, an der die Quelle zerbricht) und kehrt dann bei jeder
# Wiederholung zurueck. Einer deterministischen Absage keinen Wiederholungsrat
# geben — weder im Code noch in der Meldung ans Modell. 502, 503 und 504 sagen
# dagegen ueber die Anfrage nichts: Ein Gateway hat die Quelle nicht erreicht.
_TRANSIENT_STATUS: frozenset[int] = frozenset({502, 503, 504})

# Pausen nach dem ersten und zweiten Fehlversuch, also drei Versuche. Kurz,
# weil ein Tool-Aufruf auf die Antwort wartet: im schlimmsten Fall 1,5 s mehr.
_RETRY_PAUSEN: tuple[float, ...] = (0.5, 1.0)

# Modul-Alias statt `asyncio.sleep` direkt: Ein Test patcht diesen Namen. Ein
# `monkeypatch.setattr(asyncio, "sleep", ...)` entschaerfte das Warten im ganzen
# Prozess, auch in der Event-Loop von anyio.
_sleep = asyncio.sleep

# Egress-Allow-List (SEC-021). Alle ausgehenden HTTP-Calls müssen auf einen
# dieser Hosts gehen — Defense-in-Depth gegen Redirect-Hijack und gegen
# spätere Drift in Richtung "alle Domains erlaubt".
ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "www.envidat.ch",
        "envidat.ch",
    }
)


def assert_host_allowed(url: str) -> None:
    """Wirft PermissionError wenn der URL-Host nicht in ALLOWED_HOSTS ist."""
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise PermissionError(f"Host not in egress allow-list: {host!r}")


# WSL-Forschungsdomänen → kuratierte Suchbegriffe
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "wald": [
        "forest",
        "wald",
        "trees",
        "sanasilva",
        "LFI",
        "bark beetle",
        "defoliation",
        "beech",
        "spruce",
        "forest inventory",
        "waldbrand",
    ],
    "biodiversitaet": [
        "biodiversity",
        "species",
        "habitat",
        "vegetation",
        "insects",
        "fungi",
        "lichens",
        "birds",
        "mammals",
        "invertebrates",
        "plant diversity",
        "ecosystem",
    ],
    "naturgefahren": [
        "avalanche",
        "debris flow",
        "landslide",
        "rockfall",
        "flood",
        "erosion",
        "sediment",
        "hazard",
        "murgang",
        "steinschlag",
        "rutschung",
    ],
    "schnee_eis": [
        "snow",
        "avalanche",
        "glacier",
        "permafrost",
        "ice",
        "snowpack",
        "snowmelt",
        "firn",
        "SLF",
        "snow depth",
        "snowcover",
    ],
    "landschaft": [
        "landscape",
        "land use",
        "land cover",
        "drought",
        "remote sensing",
        "urban",
        "recreation",
        "settlement",
        "trockenheit",
        "landnutzung",
        "fernerkundung",
    ],
}

# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────


def _make_client() -> httpx.AsyncClient:
    """Erstellt einen konfigurierten HTTP-Client.

    follow_redirects=False (SEC-005, SEC-021): Cross-Origin-Redirects sind
    nicht erlaubt. Bei einem 3xx-Response wirft httpx auf raise_for_status,
    sodass Redirect-Hijacking kein stiller Failure-Mode ist.
    """
    assert_host_allowed(ENVIDAT_API_BASE)
    return httpx.AsyncClient(
        base_url=ENVIDAT_API_BASE,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": f"wsl-envidat-mcp/{__version__} (github.com/malkreide/wsl-envidat-mcp)",
            "Accept": "application/json",
        },
        follow_redirects=False,
    )


async def _get(
    client: httpx.AsyncClient, path: str, params: dict[str, Any] | None = None
) -> httpx.Response:
    """GET mit Wiederholung bei Gateway-Fehlern, sonst unveraendert.

    Wiederholt wird nur, was `_TRANSIENT_STATUS` nennt. Jede andere Antwort —
    auch ein 500 oder ein 404 — geht beim ersten Mal zurueck. Bleibt der
    Gateway-Fehler bis zum letzten Versuch, kommt diese letzte Antwort zurueck,
    und `_parse_response` wirft wie bisher.

    Nur fuer GET: Alle Aufrufe dieses Moduls lesen. Ein schreibender Aufruf
    duerfte so nicht wiederholt werden.
    """
    for pause in (*_RETRY_PAUSEN, None):
        response = await client.get(path, params=params)
        if response.status_code not in _TRANSIENT_STATUS or pause is None:
            return response
        logger.info(
            "EnviDat %s antwortet mit HTTP %s, neuer Versuch in %.1f s",
            path,
            response.status_code,
            pause,
        )
        await _sleep(pause)
    raise AssertionError("unerreichbar: die Schleife endet mit pause=None")


def _ist_html(response: httpx.Response) -> bool:
    """Ist der Antwortkoerper eine HTML-Seite statt einer Auskunft?

    Beides wird geprueft, weil keines allein genuegt: Fehlerseiten von Gateways
    kommen nicht immer mit `text/html`, und der Content-Type der 502-Antworten
    vom November 2026 ist nicht aufgezeichnet — nur ihr Anfang.
    """
    if "html" in response.headers.get("content-type", "").lower():
        return True
    return response.text.lstrip()[:15].lower().startswith(("<!doctype", "<html"))


class UpstreamSchemaError(ValueError):
    """Die Antwort kam an, sieht aber anders aus, als der Code sie liest.

    Erbt von ``ValueError``, damit ``handle_api_error`` sie weiterhin als
    API-Fehler formatiert statt als "Unerwarteter Fehler" — und trotzdem von
    einem echten CKAN-Fehler unterscheidbar bleibt, denn die Behebung ist eine
    andere: Bei einem CKAN-Fehler hat die Quelle geantwortet, hier hat sie sich
    geändert.
    """


def _parse_response(response: httpx.Response, action: str) -> Any:
    """Parst eine CKAN-API-Antwort und wirft bei Fehlern eine Exception.

    Der Rückgabetyp ist ``Any`` und nicht ``dict``: ``organization_list`` und
    ``tag_list`` liefern eine Liste. Die alte Annotation war falsch, und der
    alte Default ``{}`` war es doppelt — für diese beiden Aktionen war der
    Ersatzwert nicht einmal vom richtigen Typ.

    ``result`` wird bestätigt statt gedefaultet (FID-006). Ein
    ``.get("result", {})`` macht aus jeder Strukturänderung ein gültiges leeres
    Ergebnis, und für das Modell ist das nicht von "die Quelle kennt das nicht"
    zu unterscheiden.
    """
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise UpstreamSchemaError(
            f"CKAN '{action}': Antwort ist {type(data).__name__} und kein Objekt. "
            "Erwartet wird die CKAN-Hülle mit 'success' und 'result'."
        )
    if not data.get("success"):
        error = data.get("error", {})
        raise ValueError(f"CKAN API Fehler bei '{action}': {error}")
    if "result" not in data:
        raise UpstreamSchemaError(
            f"CKAN '{action}': Antwort ohne 'result'. Vorhandene Schlüssel: "
            f"{sorted(data)}. Das ist keine Leermenge — die Struktur der Quelle "
            "hat sich geändert oder die Aktion war nie richtig."
        )
    return data["result"]


def ckan_results(result: object) -> list:
    """Die Trefferliste eines bestaetigten ``result``-Blocks, oder laut scheitern.

    Der Fix vom 2026-08-07 bestaetigte ``result`` und hoerte dort auf. Die Ebene
    darunter blieb offen: ``result.get("results", [])`` in den Formatierern
    machte aus einer Strukturaenderung weiterhin «0 Datensaetze gefunden» —
    dieselbe Antwort wie eine korrekte Suche ohne Treffer (FID-006).

    CKAN liefert ``results`` und ``count`` bei ``package_search`` immer, auch
    bei null Treffern. Bestaetigt wird die Anwesenheit, nicht der Inhalt.
    """
    if not isinstance(result, dict):
        raise UpstreamSchemaError(
            f"CKAN 'package_search': `result` ist {type(result).__name__} und kein Objekt."
        )
    missing = [f for f in ("results", "count") if f not in result]
    if missing:
        raise UpstreamSchemaError(
            f"CKAN 'package_search': `result` ohne {missing}. Vorhandene "
            f"Schluessel: {sorted(result)}. CKAN liefert 'results' und 'count' "
            "auch bei null Treffern — dies ist keine leere Suche."
        )
    return result["results"]


def handle_api_error(e: Exception, context: str = "") -> str:
    """Gibt eine einheitliche, hilfreiche Fehlermeldung zurück."""
    prefix = f"[{context}] " if context else ""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 404:
            return f"{prefix}Fehler: Ressource nicht gefunden. Bitte ID/Slug prüfen."
        if code == 403:
            return f"{prefix}Fehler: Kein Zugriff (403 Forbidden)."
        if code == 429:
            return f"{prefix}Fehler: Rate-Limit erreicht. Bitte kurz warten."
        reason = e.response.reason_phrase
        if code in _TRANSIENT_STATUS:
            # Hier ist der Wiederholungsrat richtig — anders als bei einem 400
            # oder 500: Ein Gateway-Fehler sagt nichts ueber die Anfrage.
            return (
                f"{prefix}Fehler: Die Quelle antwortet mit HTTP {code} {reason} – "
                "eine Störung auf Seiten von www.envidat.ch, keine Aussage über "
                "die Daten. Ein späterer Versuch kann gelingen."
            )
        # Den Status mitfuehren, nicht den Koerper, wenn der Koerper eine
        # HTML-Seite ist. Bis November 2026 standen hier die ersten 200 Zeichen
        # jeder Antwort — bei einem 502 also `<!DOCTYPE html>\n<html lang="en">`
        # und ein Stueck `<head>`, ohne ein einziges Wort Auskunft. Ein
        # JSON-Fehlerkoerper von CKAN (etwa bei einem 409) ist dagegen eine
        # Auskunft der Quelle und bleibt stehen.
        detail = "" if _ist_html(e.response) else f" – {e.response.text[:200]}"
        return f"{prefix}Fehler: HTTP {code} {reason}{detail}"
    if isinstance(e, httpx.TimeoutException):
        return f"{prefix}Fehler: Zeitüberschreitung. Bitte erneut versuchen."
    if isinstance(e, ValueError):
        return f"{prefix}API-Fehler: {e}"
    return f"{prefix}Unerwarteter Fehler: {type(e).__name__}: {e}"


# ─── API-Funktionen ───────────────────────────────────────────────────────────


async def ckan_package_search(
    query: str = "",
    fq: str = "",
    rows: int = 20,
    start: int = 0,
    sort: str = "score desc, metadata_modified desc",
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Durchsucht den EnviDat CKAN-Katalog.

    Args:
        query: Suchbegriff (Solr-Syntax möglich, z.B. 'snow avalanche')
        fq: Filter-Query (z.B. 'organization:slf')
        rows: Anzahl Ergebnisse
        start: Offset für Paginierung
        sort: Sortierung (z.B. 'metadata_modified desc')
        extras: Zusätzliche Parameter (z.B. {'ext_bbox': '8.0,47.0,9.5,47.8'})
    """
    params: dict[str, Any] = {
        "q": query or "*:*",
        "rows": rows,
        "start": start,
        "sort": sort,
    }
    if fq:
        params["fq"] = fq
    if extras:
        params.update(extras)

    async with _make_client() as client:
        response = await _get(client, "/package_search", params=params)
        return _parse_response(response, "package_search")


async def ckan_package_show(id_or_slug: str) -> dict[str, Any]:
    """Gibt vollständige Metadaten eines Datensatzes zurück."""
    async with _make_client() as client:
        response = await _get(client, "/package_show", params={"id": id_or_slug})
        return _parse_response(response, "package_show")


async def ckan_organization_list(all_fields: bool = False) -> list[Any]:
    """Listet alle WSL-Forschungseinheiten/Organisationen auf."""
    params: dict[str, Any] = {"all_fields": all_fields}
    async with _make_client() as client:
        response = await _get(client, "/organization_list", params=params)
        return _parse_response(response, "organization_list")


async def ckan_organization_show(id_or_name: str, include_datasets: bool = False) -> dict[str, Any]:
    """Gibt Details einer Organisation/Forschungseinheit zurück."""
    params: dict[str, Any] = {
        "id": id_or_name,
        "include_datasets": include_datasets,
    }
    async with _make_client() as client:
        response = await _get(client, "/organization_show", params=params)
        return _parse_response(response, "organization_show")


async def ckan_tag_list(query: str = "", vocabulary_id: str = "") -> list[str]:
    """Listet verfügbare Tags/Schlagwörter im Katalog auf."""
    params: dict[str, Any] = {}
    if query:
        params["query"] = query
    if vocabulary_id:
        params["vocabulary_id"] = vocabulary_id
    async with _make_client() as client:
        response = await _get(client, "/tag_list", params=params)
        return _parse_response(response, "tag_list")


async def ckan_status_show() -> dict[str, Any]:
    """Gibt Status-Informationen des EnviDat-Portals zurück."""
    async with _make_client() as client:
        response = await _get(client, "/status_show")
        return _parse_response(response, "status_show")


def format_dataset_summary(pkg: dict[str, Any], include_resources: bool = True) -> str:
    """Formatiert einen Datensatz als lesbare Markdown-Zusammenfassung."""
    title = pkg.get("title") or pkg.get("name", "–")
    name = pkg.get("name", "–")
    notes = (pkg.get("notes") or "Keine Beschreibung vorhanden.")[:400]
    modified = pkg.get("metadata_modified", "")[:10]
    org_dict = pkg.get("organization") or {}
    org = org_dict.get("title") or org_dict.get("name", "–")
    tags = [t.get("name", "") for t in pkg.get("tags", [])]
    num_res = len(pkg.get("resources", []))
    url = f"{ENVIDAT_PORTAL}/dataset/{name}"

    lines = [
        f"### {title}",
        f"- **ID/Slug:** `{name}`",
        f"- **Organisation:** {org}",
        f"- **Letzte Änderung:** {modified}",
        f"- **Ressourcen:** {num_res}",
        f"- **Tags:** {', '.join(tags[:8]) or '–'}",
        f"- **EnviDat:** [Datensatz öffnen]({url})",
        f"\n{notes}",
    ]

    if include_resources and pkg.get("resources"):
        lines.append("\n**Verfügbare Ressourcen:**")
        for r in pkg["resources"][:5]:
            r_name = r.get("name") or r.get("id", "Unbekannt")
            r_format = r.get("format", "–").upper()
            r_url = r.get("url", "–")
            lines.append(f"  - `{r_format}` [{r_name}]({r_url})")
        if num_res > 5:
            lines.append(f"  - *(+{num_res - 5} weitere Ressourcen auf EnviDat)*")

    return "\n".join(lines)


def build_domain_query(domain: str) -> str:
    """Gibt den primären Suchbegriff für eine WSL-Forschungsdomäne zurück.

    Hintergrund: Die CKAN/Solr-Instanz von EnviDat behandelt 'OR' als Stopwort
    und reduziert damit die Trefferzahl. Einzelne Suchbegriffe liefern deshalb
    konsistent bessere Ergebnisse. Die Begriffe sind nach Trefferhäufigkeit gewählt.
    """
    _PRIMARY: dict[str, str] = {
        "wald": "forest",
        "biodiversitaet": "species",
        "naturgefahren": "avalanche",
        "schnee_eis": "snow",
        "landschaft": "landscape",
    }
    return _PRIMARY.get(domain.lower(), domain)
