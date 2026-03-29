"""HTTP-Client für die EnviDat CKAN API.

WSL – Eidg. Forschungsanstalt für Wald, Schnee und Landschaft.

API-Basis: https://www.envidat.ch/api/action/
Dokumentation: https://docs.ckan.org/en/latest/api/index.html
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ─── Konstanten ───────────────────────────────────────────────────────────────

ENVIDAT_API_BASE = "https://www.envidat.ch/api/action"
ENVIDAT_PORTAL = "https://www.envidat.ch"
REQUEST_TIMEOUT = 30.0  # Sekunden

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
    """Erstellt einen konfigurierten HTTP-Client."""
    return httpx.AsyncClient(
        base_url=ENVIDAT_API_BASE,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": "wsl-envidat-mcp/0.1.0 (github.com/malkreide/wsl-envidat-mcp)",
            "Accept": "application/json",
        },
        follow_redirects=True,
    )


def _parse_response(response: httpx.Response, action: str) -> dict[str, Any]:
    """Parst eine CKAN-API-Antwort und wirft bei Fehlern eine Exception."""
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        error = data.get("error", {})
        raise ValueError(f"CKAN API Fehler bei '{action}': {error}")
    return data.get("result", {})


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
        return f"{prefix}Fehler: HTTP {code} – {e.response.text[:200]}"
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
        response = await client.get("/package_search", params=params)
        return _parse_response(response, "package_search")


async def ckan_package_show(id_or_slug: str) -> dict[str, Any]:
    """Gibt vollständige Metadaten eines Datensatzes zurück."""
    async with _make_client() as client:
        response = await client.get("/package_show", params={"id": id_or_slug})
        return _parse_response(response, "package_show")


async def ckan_organization_list(all_fields: bool = False) -> list[Any]:
    """Listet alle WSL-Forschungseinheiten/Organisationen auf."""
    params: dict[str, Any] = {"all_fields": all_fields}
    async with _make_client() as client:
        response = await client.get("/organization_list", params=params)
        return _parse_response(response, "organization_list")


async def ckan_organization_show(id_or_name: str, include_datasets: bool = False) -> dict[str, Any]:
    """Gibt Details einer Organisation/Forschungseinheit zurück."""
    params: dict[str, Any] = {
        "id": id_or_name,
        "include_datasets": include_datasets,
    }
    async with _make_client() as client:
        response = await client.get("/organization_show", params=params)
        return _parse_response(response, "organization_show")


async def ckan_tag_list(query: str = "", vocabulary_id: str = "") -> list[str]:
    """Listet verfügbare Tags/Schlagwörter im Katalog auf."""
    params: dict[str, Any] = {}
    if query:
        params["query"] = query
    if vocabulary_id:
        params["vocabulary_id"] = vocabulary_id
    async with _make_client() as client:
        response = await client.get("/tag_list", params=params)
        return _parse_response(response, "tag_list")


async def ckan_status_show() -> dict[str, Any]:
    """Gibt Status-Informationen des EnviDat-Portals zurück."""
    async with _make_client() as client:
        response = await client.get("/status_show")
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
