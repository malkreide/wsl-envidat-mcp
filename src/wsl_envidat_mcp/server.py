"""WSL/EnviDat MCP Server

MCP-Server für die Umweltforschungs- und Monitoringdaten der Eidgenössischen Forschungsanstalt
für Wald, Schnee und Landschaft (WSL) via EnviDat (www.envidat.ch).

Domänen: Wald · Biodiversität · Naturgefahren · Schnee & Eis · Landschaft
Datensätze: 1'000+ Forschungsdatensätze | Zeitreihen: bis 130 Jahre | Stationen: 6'000+
API: CKAN-basiert, kein API-Schlüssel erforderlich

Enthält 12 Tools und 2 Resources.
"""

from __future__ import annotations

import json
import logging
import sys
from enum import Enum
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from wsl_envidat_mcp.api_client import (
    DOMAIN_KEYWORDS,
    ENVIDAT_PORTAL,
    build_domain_query,
    ckan_organization_list,
    ckan_organization_show,
    ckan_package_search,
    ckan_package_show,
    ckan_tag_list,
    format_dataset_summary,
    handle_api_error,
)

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("wsl_envidat_mcp")

# ─── MCP Server ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    "wsl-envidat-mcp",
    instructions=(
        "Dieser Server gibt Zugriff auf Umweltforschungs- und Monitoringdaten der WSL "
        "(Eidg. Forschungsanstalt für Wald, Schnee und Landschaft) via EnviDat. "
        "Verwende wsl_search_datasets für freie Suche, wsl_search_by_domain für "
        "thematische Suche (Wald, Biodiversität, Naturgefahren, Schnee & Eis, Landschaft), "
        "und wsl_get_dataset für vollständige Metadaten inkl. Download-URLs. "
        "Kein API-Schlüssel erforderlich. Alle Daten sind öffentlich zugänglich."
    ),
)

# ─── Enums & Modelle ──────────────────────────────────────────────────────────


class WSLDomain(str, Enum):
    """WSL-Forschungsdomänen."""

    WALD = "wald"
    BIODIVERSITAET = "biodiversitaet"
    NATURGEFAHREN = "naturgefahren"
    SCHNEE_EIS = "schnee_eis"
    LANDSCHAFT = "landschaft"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class SearchDatasetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ...,
        description=(
            "Suchbegriff(e) für Datensätze. Solr-Syntax möglich. "
            "Beispiele: 'snow avalanche', 'forest biodiversity Switzerland', "
            "'bark beetle spruce', 'drought 2018'"
        ),
        min_length=1,
        max_length=200,
    )
    limit: Optional[int] = Field(
        default=10,
        description="Maximale Anzahl Ergebnisse (1–50)",
        ge=1,
        le=50,
    )
    offset: Optional[int] = Field(
        default=0,
        description="Offset für Paginierung",
        ge=0,
    )
    organization: Optional[str] = Field(
        default=None,
        description=(
            "Filter nach WSL-Forschungseinheit (Slug). "
            "Beispiele: 'wsl', 'slf' (Schnee- und Lawinenforschung)"
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' (lesbar) oder 'json' (maschinenlesbar)",
    )


class GetDatasetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id_or_slug: str = Field(
        ...,
        description=(
            "Dataset-ID (UUID) oder Slug (URL-Name). "
            "Beispiele: 'fatal-avalanche-accidents-in-switzerland-since-1936-37', "
            "'swiss-national-forest-inventory-lfi'"
        ),
        min_length=1,
        max_length=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' (lesbar) oder 'json' (maschinenlesbar)",
    )


class SearchByDomainInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    domain: WSLDomain = Field(
        ...,
        description=(
            "WSL-Forschungsdomäne: "
            "'wald' (Forstinventar, Waldschäden, Borkenkäfer), "
            "'biodiversitaet' (Arten, Habitate, Flechten, Pilze), "
            "'naturgefahren' (Lawinen, Rutschungen, Murgänge, Überschwemmungen), "
            "'schnee_eis' (Schneedecke, Gletscher, Permafrost, SLF-Daten), "
            "'landschaft' (Landnutzung, Trockenheit, Naherholung, Fernerkundung)"
        ),
    )
    limit: Optional[int] = Field(
        default=10,
        description="Maximale Anzahl Ergebnisse (1-30)",
        ge=1,
        le=30,
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetOrganizationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(
        ...,
        description=(
            "Organisations-Slug. Beispiele: 'wsl', 'slf', 'forest-dynamics', 'mountain-ecosystems'"
        ),
        min_length=1,
        max_length=100,
    )
    include_datasets: Optional[bool] = Field(
        default=True,
        description="Datensätze der Organisation mitausgeben",
    )


class SearchByLocationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    min_lon: float = Field(
        ...,
        description="West-Longitude (Dezimalgrad), z.B. 5.95",
        ge=-180,
        le=180,
    )
    min_lat: float = Field(
        ...,
        description="Sued-Latitude (Dezimalgrad), z.B. 45.8",
        ge=-90,
        le=90,
    )
    max_lon: float = Field(
        ...,
        description="Ost-Longitude (Dezimalgrad), z.B. 10.5",
        ge=-180,
        le=180,
    )
    max_lat: float = Field(
        ...,
        description="Nord-Latitude (Dezimalgrad), z.B. 47.8",
        ge=-90,
        le=90,
    )
    query: Optional[str] = Field(
        default=None,
        description="Optionaler zusätzlicher Suchbegriff zur Einschränkung",
    )
    limit: Optional[int] = Field(default=10, ge=1, le=30)

    @field_validator("max_lon")
    @classmethod
    def validate_lon_range(cls, v: float, info: Any) -> float:
        if "min_lon" in (info.data or {}) and v <= info.data["min_lon"]:
            raise ValueError("max_lon muss grösser als min_lon sein")
        return v

    @field_validator("max_lat")
    @classmethod
    def validate_lat_range(cls, v: float, info: Any) -> float:
        if "min_lat" in (info.data or {}) and v <= info.data["min_lat"]:
            raise ValueError("max_lat muss grösser als min_lat sein")
        return v


class ListTagsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: Optional[str] = Field(
        default=None,
        description="Optionaler Suchbegriff für Tags (z.B. 'snow', 'forest')",
        max_length=100,
    )
    limit: Optional[int] = Field(default=50, ge=1, le=200)


class GetRecentDatasetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    limit: Optional[int] = Field(default=10, ge=1, le=30)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SimpleQueryInput(BaseModel):
    """Für spezialisierte thematische Suchen (Wald, Lawinen, Schnee, Dürre)."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    limit: Optional[int] = Field(default=8, ge=1, le=20)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# ─── Hilfsfunktion: Suchergebnisse formatieren ───────────────────────────────


def _format_search_results(
    result: dict[str, Any],
    response_format: ResponseFormat,
    title: str = "EnviDat Suchergebnisse",
) -> str:
    """Formatiert Suchergebnisse einheitlich für alle Such-Tools."""
    packages = result.get("results", [])
    count = result.get("count", 0)
    shown = len(packages)

    if response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "total_found": count,
                "shown": shown,
                "datasets": [
                    {
                        "name": p.get("name"),
                        "title": p.get("title"),
                        "notes": (p.get("notes") or "")[:300],
                        "modified": p.get("metadata_modified", "")[:10],
                        "org": (p.get("organization") or {}).get("name"),
                        "tags": [t.get("name") for t in p.get("tags", [])],
                        "resources": len(p.get("resources", [])),
                        "url": f"{ENVIDAT_PORTAL}/dataset/{p.get('name')}",
                    }
                    for p in packages
                ],
            },
            indent=2,
            ensure_ascii=False,
        )

    if not packages:
        return "Keine Datensätze gefunden. Bitte Suchbegriff anpassen."

    lines = [f"## {title}", f"**{count} Datensätze gefunden** (zeige {shown}):\n"]
    for i, pkg in enumerate(packages, 1):
        lines.append(f"---\n**{i}.** {format_dataset_summary(pkg, include_resources=False)}")

    lines.append(
        f"\n---\n*Alle Datensätze auf [EnviDat]({ENVIDAT_PORTAL}) · "
        "API: https://www.envidat.ch/api/action/*"
    )
    return "\n".join(lines)


# ─── Tool 1: Datensätze suchen ────────────────────────────────────────────────


@mcp.tool(
    name="wsl_search_datasets",
    annotations={
        "title": "EnviDat Datensätze suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_search_datasets(params: SearchDatasetsInput) -> str:
    """Durchsucht den EnviDat-Katalog der WSL nach Umweltforschungsdatensätzen.

    Zugriff auf 1'000+ Datensätze aus 5 WSL-Forschungsdomänen: Wald, Biodiversität,
    Naturgefahren, Schnee & Eis und Landschaft. Zeitreihen bis 130 Jahre.
    Solr-Syntax möglich (AND, OR, Anführungszeichen für Phrasen).

    Args:
        params (SearchDatasetsInput): Suchparameter mit:
            - query (str): Suchbegriff(e)
            - limit (int): Anzahl Ergebnisse (Standard: 10)
            - offset (int): Offset für Paginierung
            - organization (str): Filter nach WSL-Forschungseinheit
            - response_format: 'markdown' oder 'json'

    Returns:
        str: Liste gefundener Datensätze mit Titel, Organisation, Tags und URL
    """
    try:
        fq = f"organization:{params.organization}" if params.organization else ""
        result = await ckan_package_search(
            query=params.query,
            fq=fq,
            rows=params.limit,
            start=params.offset,
        )
        return _format_search_results(
            result,
            params.response_format,
            title=f"Suchergebnisse für «{params.query}»",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_search_datasets")


# ─── Tool 2: Datensatz-Details ────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_dataset",
    annotations={
        "title": "EnviDat Datensatz-Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_dataset(params: GetDatasetInput) -> str:
    """Gibt vollständige Metadaten und Ressourcen (Download-URLs) eines EnviDat-Datensatzes zurück.

    Liefert Titel, Beschreibung, Autoren, Zeitraum, Räumliche Ausdehnung, DOI,
    Lizenz, alle Ressourcen (Daten-Downloads) und Projektinformationen.

    Args:
        params (GetDatasetInput): Mit:
            - id_or_slug (str): Dataset-ID (UUID) oder URL-Slug
            - response_format: 'markdown' oder 'json'

    Returns:
        str: Vollständige Metadaten inkl. Download-Links und DOI
    """
    try:
        pkg = await ckan_package_show(params.id_or_slug)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(pkg, indent=2, ensure_ascii=False)

        # Erweiterte Markdown-Ausgabe
        title = pkg.get("title") or pkg.get("name", "–")
        name = pkg.get("name", "–")
        notes = pkg.get("notes") or "Keine Beschreibung vorhanden."
        org = (pkg.get("organization") or {}).get("title", "–")
        modified = pkg.get("metadata_modified", "")[:10]
        created = pkg.get("metadata_created", "")[:10]
        tags = [t.get("name", "") for t in pkg.get("tags", [])]
        license_title = pkg.get("license_title", "–")
        doi = pkg.get("doi") or pkg.get("extras_doi", "–")
        url = f"{ENVIDAT_PORTAL}/dataset/{name}"

        # Autoren aus extras
        extras = {e.get("key"): e.get("value") for e in pkg.get("extras", [])}
        authors = extras.get("authors", extras.get("author", "–"))
        pub_year = extras.get("publication_year", "")
        spatial = extras.get("spatial", "")

        lines = [
            f"# {title}",
            f"\n**Slug:** `{name}`",
            f"**Organisation:** {org}",
            f"**Erstellt:** {created} · **Letzte Änderung:** {modified}",
            f"**Lizenz:** {license_title}",
        ]
        if doi and doi != "–":
            lines.append(f"**DOI:** https://doi.org/{doi}")
        if pub_year:
            lines.append(f"**Publikationsjahr:** {pub_year}")
        if authors and authors != "–":
            lines.append(f"**Autor(en):** {authors[:300]}")
        if tags:
            lines.append(f"**Tags:** {', '.join(tags)}")

        lines.append(f"\n## Beschreibung\n{notes}")

        if spatial:
            try:
                sp = json.loads(spatial)
                bbox_str = json.dumps(
                    sp.get("bbox") or sp,
                    ensure_ascii=False,
                )
                lines.append(f"\n**Räumliche Ausdehnung:** {bbox_str}")
            except Exception:
                lines.append(f"\n**Räumliche Ausdehnung:** {spatial[:200]}")

        resources = pkg.get("resources", [])
        if resources:
            lines.append(f"\n## Ressourcen ({len(resources)} Dateien)\n")
            for r in resources:
                r_name = r.get("name") or r.get("id", "Unbekannt")
                r_format = (r.get("format") or "–").upper()
                r_size = r.get("size")
                r_url = r.get("url", "–")
                r_desc = r.get("description", "")
                size_str = f" · {int(r_size) // 1024} KB" if r_size else ""
                desc_str = f" – {r_desc[:80]}" if r_desc else ""
                lines.append(f"- **`{r_format}`** [{r_name}]({r_url}){size_str}{desc_str}")

        lines.append(f"\n---\n🔗 [Auf EnviDat öffnen]({url})")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "wsl_get_dataset")


# ─── Tool 3: Suche nach Domäne ────────────────────────────────────────────────


@mcp.tool(
    name="wsl_search_by_domain",
    annotations={
        "title": "WSL-Domäne durchsuchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_search_by_domain(params: SearchByDomainInput) -> str:
    """Sucht Datensätze in einer WSL-Forschungsdomäne mit kuratierten Suchbegriffen.

    Jede Domäne nutzt optimierte Keyword-Kombinationen für präzise Ergebnisse:
    - wald: Forstinventar (LFI), Sanasilva, Waldschäden, Borkenkäfer
    - biodiversitaet: Arten, Habitatkarte CH, Flechten, Pilze, Insekten
    - naturgefahren: Lawinenunfälle, Rutschungen, Murgänge, Steinschlag
    - schnee_eis: Schneemessreihen, Gletscher, Permafrost, SLF-Daten
    - landschaft: Landnutzung, Trockenheit, Naherholung, Fernerkundung

    Args:
        params (SearchByDomainInput): Mit:
            - domain (WSLDomain): Forschungsdomäne
            - limit (int): Anzahl Ergebnisse
            - response_format: 'markdown' oder 'json'

    Returns:
        str: Datensätze der gewählten Domäne
    """
    try:
        domain_query = build_domain_query(params.domain.value)
        result = await ckan_package_search(
            query=domain_query,
            rows=params.limit,
        )
        domain_label = {
            "wald": "🌲 Wald",
            "biodiversitaet": "🦋 Biodiversität",
            "naturgefahren": "⛰️ Naturgefahren",
            "schnee_eis": "❄️ Schnee & Eis",
            "landschaft": "🏞️ Landschaft",
        }.get(params.domain.value, params.domain.value)

        return _format_search_results(
            result,
            params.response_format,
            title=f"Forschungsdomäne {domain_label}",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_search_by_domain")


# ─── Tool 4: Räumliche Suche ──────────────────────────────────────────────────


@mcp.tool(
    name="wsl_search_by_location",
    annotations={
        "title": "Räumliche Datensatz-Suche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_search_by_location(params: SearchByLocationInput) -> str:
    """Sucht WSL/EnviDat-Datensätze in einem geografischen Begrenzungsrahmen (Bounding Box).

    Besonders nützlich für:
    - Standortspezifische Analysen (z.B. Zürich, Davos, Alpenraum)
    - Schulareal-Umgebungsanalysen (Waldbestand, Biodiversität)
    - Kantonale Umweltberichte

    Schweiz gesamt: min_lon=5.95, min_lat=45.8, max_lon=10.5, max_lat=47.8
    Kanton Zürich:  min_lon=8.35, min_lat=47.15, max_lon=8.98, max_lat=47.72

    Args:
        params (SearchByLocationInput): Bounding-Box-Koordinaten + optionaler Suchbegriff

    Returns:
        str: Datensätze im gewählten geografischen Bereich
    """
    try:
        bbox = f"{params.min_lon},{params.min_lat},{params.max_lon},{params.max_lat}"
        extras = {"ext_bbox": bbox}
        result = await ckan_package_search(
            query=params.query or "*:*",
            rows=params.limit,
            extras=extras,
        )
        location_str = (
            f"BBox [{params.min_lon:.2f},{params.min_lat:.2f}"
            f" -> {params.max_lon:.2f},{params.max_lat:.2f}]"
        )
        return _format_search_results(
            result,
            ResponseFormat.MARKDOWN,
            title=f"Datensätze in {location_str}",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_search_by_location")


# ─── Tool 5: Organisationen auflisten ─────────────────────────────────────────


@mcp.tool(
    name="wsl_list_organizations",
    annotations={
        "title": "WSL-Forschungseinheiten auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_list_organizations() -> str:
    """Listet alle WSL-Forschungseinheiten und deren Datensatz-Anzahl auf.

    Gibt einen Überblick über die Forschungsgruppen der WSL, die Daten auf
    EnviDat publiziert haben. Nützlich zur Identifikation relevanter
    Organisationen für nachfolgende Abfragen mit wsl_get_organization.

    Returns:
        str: Liste aller WSL-Forschungseinheiten mit Slug und Datensatz-Anzahl
    """
    try:
        orgs = await ckan_organization_list(all_fields=True)

        if not orgs:
            return "Keine Organisationen gefunden."

        lines = [
            "## WSL-Forschungseinheiten auf EnviDat\n",
            f"**{len(orgs)} Organisationen** mit Datensätzen:\n",
        ]
        for org in sorted(orgs, key=lambda x: x.get("package_count", 0), reverse=True):
            name = org.get("name", "–")
            title = org.get("title") or name
            count = org.get("package_count", 0)
            desc = (org.get("description") or "")[:120]
            lines.append(f"- **{title}** (`{name}`) – {count} Datensätze")
            if desc:
                lines.append(f"  _{desc}_")

        lines.append("\n*Tipp: `wsl_get_organization` für Details zu einer Einheit*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "wsl_list_organizations")


# ─── Tool 6: Organisation-Details ─────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_organization",
    annotations={
        "title": "WSL-Forschungseinheit Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_get_organization(params: GetOrganizationInput) -> str:
    """Gibt Details einer WSL-Forschungseinheit inklusive ihrer Datensätze zurück.

    Liefert Beschreibung, Kontakt und Datensatz-Übersicht einer Organisation.
    Das SLF (Institut für Schnee- und Lawinenforschung) ist als 'slf' abrufbar.

    Args:
        params (GetOrganizationInput): Mit:
            - name (str): Organisations-Slug (z.B. 'wsl', 'slf')
            - include_datasets (bool): Datensätze mitausgeben

    Returns:
        str: Organisation-Details mit optionaler Datensatz-Liste
    """
    try:
        org = await ckan_organization_show(params.name, params.include_datasets)

        title = org.get("title") or org.get("name", "–")
        name = org.get("name", "–")
        desc = org.get("description") or "Keine Beschreibung."
        count = org.get("package_count", 0)
        pkgs = org.get("packages", [])

        lines = [
            f"## {title}",
            f"**Slug:** `{name}`  |  **Datensätze:** {count}\n",
            f"{desc}\n",
        ]

        if pkgs:
            lines.append(f"### Datensätze ({min(len(pkgs), 10)} von {count})\n")
            for p in pkgs[:10]:
                p_title = p.get("title") or p.get("name", "–")
                p_name = p.get("name", "–")
                p_mod = p.get("metadata_modified", "")[:10]
                lines.append(
                    f"- [{p_title}]({ENVIDAT_PORTAL}/dataset/{p_name}) _(zuletzt: {p_mod})_"
                )
            if count > 10:
                lines.append(f"\n*+{count - 10} weitere Datensätze auf EnviDat*")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "wsl_get_organization")


# ─── Tool 7: Tags auflisten ───────────────────────────────────────────────────


@mcp.tool(
    name="wsl_list_tags",
    annotations={
        "title": "EnviDat Tags/Schlagwörter auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_list_tags(params: ListTagsInput) -> str:
    """Listet verfügbare Schlagwörter (Tags) im EnviDat-Katalog auf.

    Nützlich um herauszufinden, welche Suchbegriffe in wsl_search_datasets
    präzise Ergebnisse liefern. Unterstützt Präfix-Suche.

    Args:
        params (ListTagsInput): Mit:
            - query (str): Optionaler Suchbegriff für Tags
            - limit (int): Maximale Anzahl Tags

    Returns:
        str: Liste verfügbarer Tags/Schlagwörter
    """
    try:
        tags = await ckan_tag_list(query=params.query or "")
        filtered = tags[: params.limit]

        prefix = f"«{params.query}»" if params.query else "alle"
        return f"## EnviDat Tags ({prefix})\n\n{len(filtered)} Tags gefunden:\n\n" + ", ".join(
            f"`{t}`" for t in filtered
        )
    except Exception as e:
        return handle_api_error(e, "wsl_list_tags")


# ─── Tool 8: Aktuelle Datensätze ──────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_recent_datasets",
    annotations={
        "title": "Neuste EnviDat Datensätze",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def wsl_get_recent_datasets(params: GetRecentDatasetsInput) -> str:
    """Gibt die zuletzt publizierten oder aktualisierten EnviDat-Datensätze zurück.

    Nützlich für regelmässige Monitoring-Workflows und um neue WSL-Forschungsdaten
    zu entdecken.

    Args:
        params (GetRecentDatasetsInput): Mit limit und response_format

    Returns:
        str: Zuletzt aktualisierte Datensätze
    """
    try:
        result = await ckan_package_search(
            query="*:*",
            rows=params.limit,
            sort="metadata_modified desc",
        )
        return _format_search_results(
            result,
            params.response_format,
            title="Zuletzt aktualisierte WSL-Datensätze",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_get_recent_datasets")


# ─── Tool 9: Lawinendaten ─────────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_avalanche_data",
    annotations={
        "title": "SLF Lawinen- & Schneedaten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_avalanche_data(params: SimpleQueryInput) -> str:
    """Lawinen- und Schneedaten vom WSL-Institut fuer Schnee- und Lawinenforschung (SLF).

    Enthält u.a.:
    - Tödliche Lawinenunfälle in der Schweiz seit 1936/37
    - Langjährige Schneemessreihen (Station Stillberg Davos, 2090 m)
    - Meteorologische Langzeitdaten Hochgebirge
    - Schneephysik-Forschungsdaten

    Args:
        params (SimpleQueryInput): Anzahl Ergebnisse und Format

    Returns:
        str: Lawinen- und Schneedatensätze des SLF
    """
    try:
        result = await ckan_package_search(
            query='"avalanche" OR "snow" OR "lawine" OR "schnee" OR "SLF" OR "snowpack"',
            fq="organization:slf",
            rows=params.limit,
            sort="metadata_modified desc",
        )
        # Fallback ohne org-Filter falls SLF-Filter keine Ergebnisse liefert
        if result.get("count", 0) == 0:
            result = await ckan_package_search(
                query='"avalanche" OR "fatal avalanche" OR "snowpack" OR "snow depth"',
                rows=params.limit,
            )
        return _format_search_results(
            result,
            params.response_format,
            title="❄️ SLF Lawinen- & Schneedaten",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_get_avalanche_data")


# ─── Tool 10: Walddaten ───────────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_forest_data",
    annotations={
        "title": "WSL Walddaten & Forstinventar",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_forest_data(params: SimpleQueryInput) -> str:
    """Gibt Datensätze zum Schweizer Wald zurück, inkl. Landesforstinventar LFI.

    Enthält u.a.:
    - Schweizerisches Landesforstinventar (LFI) – Waldzustand, Vorräte, Biodiversität
    - Sanasilva-Programm (Waldschadensmonitoring seit 1983)
    - Langzeitforschungsflächen LWF
    - Walddynamik und Waldentwicklung seit 1840
    - Borkenkäfer-Monitoring
    - Bodenlösung und Nährstoffhaushalt im Wald

    Args:
        params (SimpleQueryInput): Anzahl Ergebnisse und Format

    Returns:
        str: Walddatensätze der WSL
    """
    try:
        result = await ckan_package_search(
            query=(
                '"forest" OR "wald" OR "LFI" OR "sanasilva"'
                ' OR "trees" OR "bark beetle" OR "defoliation"'
            ),
            rows=params.limit,
            sort="score desc",
        )
        return _format_search_results(
            result,
            params.response_format,
            title="🌲 Walddaten & Forstinventar (LFI)",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_get_forest_data")


# ─── Tool 11: Naturgefahren ───────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_naturgefahren_data",
    annotations={
        "title": "WSL Naturgefahren-Daten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_naturgefahren_data(params: SimpleQueryInput) -> str:
    """Gibt Datensätze zu Naturgefahren in der Schweiz zurück.

    Enthält u.a.:
    - Tödliche Lawinenunfälle seit 1936/37
    - Murgang- und Rutschungsereignisse
    - Steinschlag- und Felssturzdaten
    - Schwemmkegel-Morphologie
    - Sedimenttransport in Gebirgsbächen
    - Hochwasserereignisse

    Relevant für: Raumplanung, Schulhausstandort-Bewertungen,
    Katastrophenschutz, Klimafolgenabschätzung.

    Args:
        params (SimpleQueryInput): Anzahl Ergebnisse und Format

    Returns:
        str: Naturgefahren-Datensätze der WSL
    """
    try:
        result = await ckan_package_search(
            query=(
                '"natural hazard" OR "avalanche" OR "debris flow" OR "landslide" '
                'OR "rockfall" OR "murgang" OR "rutschung" OR "steinschlag" OR "flood"'
            ),
            rows=params.limit,
            sort="score desc",
        )
        return _format_search_results(
            result,
            params.response_format,
            title="⛰️ Naturgefahren-Daten der WSL",
        )
    except Exception as e:
        return handle_api_error(e, "wsl_get_naturgefahren_data")


# ─── Tool 12: Katalog-Statistiken ─────────────────────────────────────────────


@mcp.tool(
    name="wsl_catalog_stats",
    annotations={
        "title": "EnviDat Katalog-Übersicht",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_catalog_stats() -> str:
    """Gibt eine Übersicht über den EnviDat-Katalog zurück: Domänen, Organisationen, Datenmenge.

    Nützlich als Einstiegspunkt: zeigt was im Katalog verfügbar ist,
    welche WSL-Forschungsdomänen besonders viele Datensätze haben,
    und wie der Katalog strukturiert ist.

    Returns:
        str: Statistiken und Struktur des EnviDat-Katalogs
    """
    try:
        # Parallel: Gesamtanzahl + Domain-Counts + Orgs
        total_result = await ckan_package_search(query="*:*", rows=1)
        total = total_result.get("count", 0)

        orgs = await ckan_organization_list(all_fields=True)
        num_orgs = len(orgs)

        # Domain-Counts schätzen
        domain_counts: dict[str, int] = {}
        for domain_key in DOMAIN_KEYWORDS:
            q = build_domain_query(domain_key)
            r = await ckan_package_search(query=q, rows=1)
            domain_counts[domain_key] = r.get("count", 0)

        domain_labels = {
            "wald": "🌲 Wald",
            "biodiversitaet": "🦋 Biodiversität",
            "naturgefahren": "⛰️ Naturgefahren",
            "schnee_eis": "❄️ Schnee & Eis",
            "landschaft": "🏞️ Landschaft",
        }

        lines = [
            "# EnviDat – Katalog-Übersicht",
            f"\n**Portal:** {ENVIDAT_PORTAL}",
            "**Betreiber:** WSL – Eidg. Forschungsanstalt für Wald, Schnee und Landschaft",
            "**API:** CKAN (kein API-Schlüssel erforderlich)",
            "\n## Zahlen",
            f"- **Datensätze gesamt:** {total:,}",
            f"- **Forschungseinheiten:** {num_orgs}",
            "- **Monitoring-Stationen:** 6'000+",
            "- **Längste Zeitreihen:** bis 130 Jahre",
            "\n## Datensätze nach Domäne (Näherungswerte)",
        ]
        for key, label in domain_labels.items():
            count = domain_counts.get(key, 0)
            lines.append(f"  - {label}: ~{count} Datensätze")

        lines += [
            "\n## Top-Forschungseinheiten",
        ]
        top_orgs = sorted(orgs, key=lambda x: x.get("package_count", 0), reverse=True)[:6]
        for org in top_orgs:
            lines.append(
                f"  - **{org.get('title') or org.get('name')}** "
                f"(`{org.get('name')}`) – {org.get('package_count', 0)} Datensätze"
            )

        lines += [
            "\n## Weiterführende Ressourcen",
            f"- [EnviDat Portal]({ENVIDAT_PORTAL})",
            "- [Lawinenbulletin SLF](https://www.slf.ch/de/lawinenbulletin-und-schneesituation.html)",
            "- [Landesforstinventar LFI](https://www.lfi.ch)",
            "- [Trockenheitsmonitor](https://www.drought.ch)",
            "- [Waldschutz Schweiz](https://waldschutz.wsl.ch)",
        ]

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "wsl_catalog_stats")


# ─── Resources ────────────────────────────────────────────────────────────────


@mcp.resource("envidat://organization/{name}")
async def get_organization_resource(name: str) -> str:
    """WSL-Forschungseinheit als MCP-Ressource.

    URI: envidat://organization/{name}
    Beispiel: envidat://organization/slf
    """
    try:
        org = await ckan_organization_show(name, include_datasets=True)
        return json.dumps(org, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("envidat://domain/{domain}")
async def get_domain_resource(domain: str) -> str:
    """WSL-Forschungsdomäne als MCP-Ressource mit Top-Datensätzen.

    URI: envidat://domain/{domain}
    Gültige Werte: wald, biodiversitaet, naturgefahren, schnee_eis, landschaft
    """
    try:
        query = build_domain_query(domain)
        result = await ckan_package_search(query=query, rows=10, sort="score desc")
        return json.dumps(
            {
                "domain": domain,
                "total": result.get("count", 0),
                "datasets": [
                    {
                        "name": p.get("name"),
                        "title": p.get("title"),
                        "org": (p.get("organization") or {}).get("name"),
                        "url": f"{ENVIDAT_PORTAL}/dataset/{p.get('name')}",
                    }
                    for p in result.get("results", [])
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Startet den WSL/EnviDat MCP Server."""
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    port = int(os.environ.get("PORT", "8000"))

    logger.info("WSL/EnviDat MCP Server startet (Transport: %s)", transport)

    if transport == "streamable_http":
        mcp.run(transport="streamable_http", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
