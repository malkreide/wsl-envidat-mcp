"""WSL/EnviDat MCP Server

MCP-Server für die Umweltforschungs- und Monitoringdaten der Eidgenössischen Forschungsanstalt
für Wald, Schnee und Landschaft (WSL) via EnviDat (www.envidat.ch).

Domänen: Wald · Biodiversität · Naturgefahren · Schnee & Eis · Landschaft
Datensätze: 1'000+ Forschungsdatensätze | Zeitreihen: bis 130 Jahre | Stationen: 6'000+
API: CKAN-basiert, kein API-Schlüssel erforderlich

Enthält 10 Tools und 2 Resources (seit v0.2.0; vorher 12 Tools).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Optional

import structlog
from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import LATEST_PROTOCOL_VERSION, CallToolResult, TextContent
from pydantic import BaseModel, ConfigDict, Field, model_validator

from wsl_envidat_mcp import __version__
from wsl_envidat_mcp.api_client import (
    DOMAIN_KEYWORDS,
    ENVIDAT_PORTAL,
    build_domain_query,
    ckan_organization_list,
    ckan_organization_show,
    ckan_package_search,
    ckan_package_show,
    ckan_results,
    ckan_tag_list,
    format_dataset_summary,
    handle_api_error,
)

# ─── Protocol-Version ─────────────────────────────────────────────────────────

# MCP-Spec, gegen die dieser Server getestet wurde (ARCH-012). Bei einem
# Upgrade des `mcp`-SDK auf eine neuere Spec-Version diese Konstante bumpen
# und mit dem MCP Inspector validieren. LATEST_PROTOCOL_VERSION kommt aus
# dem SDK und kann beim Upgrade abweichen — Drift wird sichtbar geloggt.
# Der Wert stand auf "2025-11-25", waehrend das gepinnte SDK "2026-07-28"
# aushandelt. Gemeldet wurde das durchaus — der Drift-Zweig weiter unten loggt
# bei jedem Start eine Warnung —, nur liest die niemand, und rot wurde nichts.
# Eine Warnung ist kein Gate. `tests/test_protocol_version.py` haelt den Wert
# jetzt gegen `LATEST_PROTOCOL_VERSION`.
SUPPORTED_MCP_PROTOCOL_VERSION = "2026-07-28"


# ─── Logging ──────────────────────────────────────────────────────────────────

# Strukturierte JSON-Logs an stderr (OBS-003, OBS-004). stdout bleibt für
# das JSON-RPC-Protokoll reserviert. RFC-5424-Severities werden über die
# Standard-Python-Levels abgebildet.
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    stream=sys.stderr,
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("wsl_envidat_mcp")

# ─── MCP Server ───────────────────────────────────────────────────────────────

# SEP-2549, Spec 2026-07-28: die auflistenden Methoden tragen `ttlMs` und
# `cacheScope`. Das SDK setzt beides auf «sofort veraltet, nie geteilt» — ein
# Server ohne `cache_hints` verhaelt sich also nicht neutral, sondern laesst
# jeden Client bei jeder Verbindung neu auflisten, fuer Verzeichnisse, die beim
# Import feststehen und sich zur Laufzeit des Prozesses nicht aendern koennen.
#
# `public` folgt aus der Sache, nicht aus Bequemlichkeit: die 10 Tools werden
# per Dekorator beim Import registriert, es gibt keine Filterung nach Aufrufer.
# Sobald eine Liste vom Aufrufer abhaengt, muss der Scope im selben Commit auf
# `private` wechseln.
#
# `resources/read` und `prompts/get` stehen bewusst nicht dabei: das waere eine
# Zusicherung ueber den INHALT statt ueber das Verzeichnis.
LIST_CACHE_TTL_MS = 300_000

# Annotiert, nicht inferiert: `MCPServer` nimmt
# `Mapping[CacheableMethod, CacheHint]`, und ein Dict-Literal ohne Annotation
# inferiert mypy als `str`. Zur Laufzeit stimmt beides — ein `mypy src/`-Gate
# meldet den Unterschied, die Tests nicht.
CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/templates/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "server/discover": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
}

# Spec 2026-07-28 fuehrt `serverInfo` als `Implementation` mit sechs Feldern;
# dieser Server fuellte zwei davon, und eines davon leer. Gemessen ueber eine
# `ClientSession`: `{"name": "wsl-envidat-mcp", "version": ""}`.
#
# `version=""` ist der teure Teil. Die Nummer wird an vier Stellen
# gleichgehalten — `pyproject.toml`, `server.json`, beide README-Badges —, und
# `scripts/check_version_sync.py` haelt dieses Gate. Nur erreichte sie genau
# die Stelle nicht, an der ein Client sie liest: den Draht. Wer einen Bericht
# bekommt, dieser Server verhalte sich falsch, kann ohne sie nicht sagen,
# welcher Build gemeint ist.
#
# Der Wert kommt aus den Paket-Metadaten, nicht aus einem Literal: ein
# Literal in `src/` ist genau die Drift, die `check_version_sync.py`
# verbietet (und die im Portfolio schon falsche User-Agents erzeugt hat).
#
# `title`, `description` und `websiteUrl` sind die drei uebrigen. Sie sind
# optional — aber `title` ist der Name, den ein Client anzeigt, wenn er nicht
# den Slug zeigen will, und ohne ihn zeigt er den Slug.
mcp = MCPServer(
    "wsl-envidat-mcp",
    title="WSL / EnviDat — Umweltforschungsdaten",
    version=__version__,
    description=(
        "Umweltforschungs- und Monitoringdaten der Eidg. Forschungsanstalt fuer "
        "Wald, Schnee und Landschaft (WSL) via EnviDat."
    ),
    website_url=ENVIDAT_PORTAL,
    cache_hints=CACHE_HINTS,
    instructions=(
        "Dieser Server gibt Zugriff auf Umweltforschungs- und Monitoringdaten der WSL "
        "(Eidg. Forschungsanstalt für Wald, Schnee und Landschaft) via EnviDat. "
        "Verwende wsl_search für unifizierte Suche (kombiniert query, domain, "
        "organization und bbox), und wsl_get_dataset für vollständige Metadaten "
        "inkl. Download-URLs. Thematische Tools (wsl_get_avalanche_data, "
        "wsl_get_forest_data, wsl_get_naturgefahren_data) liefern kuratierte "
        "Subject-Matter-Queries. Kein API-Schlüssel erforderlich."
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


class SearchInput(BaseModel):
    """Unifiziertes Suchschema — kombiniert query, domain, organization und bbox.

    Mindestens einer der vier Filter (query / domain / organization / bbox)
    muss gesetzt sein. Sind mehrere gesetzt, werden sie kombiniert (AND).
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: Optional[str] = Field(
        default=None,
        description=(
            "Suchbegriff(e). Solr-Syntax möglich (Anführungszeichen für Phrasen). "
            "Hinweis: 'OR' ist ein Stopwort — einzelne präzise Begriffe liefern "
            "bessere Treffer. Beispiele: 'snow avalanche', 'bark beetle spruce'."
        ),
        max_length=200,
    )
    domain: Optional[WSLDomain] = Field(
        default=None,
        description=(
            "Kuratierte WSL-Forschungsdomäne: 'wald' (LFI/Sanasilva), "
            "'biodiversitaet' (Arten/Habitate), 'naturgefahren' (Lawinen/"
            "Rutschungen), 'schnee_eis' (Gletscher/Permafrost/SLF), "
            "'landschaft' (Landnutzung/Trockenheit). Nutzt domain-optimierte "
            "Solr-Queries — präziser als query mit dem Domain-Namen."
        ),
    )
    organization: Optional[str] = Field(
        default=None,
        description=(
            "Filter nach WSL-Forschungseinheit (Slug). Beispiele: 'wsl', "
            "'slf' (Schnee- und Lawinenforschung)."
        ),
        max_length=100,
    )
    bbox: Optional[list[float]] = Field(
        default=None,
        description=(
            "Geografischer Begrenzungsrahmen als [min_lon, min_lat, max_lon, "
            "max_lat] in Dezimalgrad. Schweiz gesamt: [5.95, 45.8, 10.5, 47.8]. "
            "Kanton Zürich: [8.35, 47.15, 8.98, 47.72]."
        ),
        min_length=4,
        max_length=4,
    )
    limit: int = Field(
        default=10,
        description="Maximale Anzahl Ergebnisse (1–50).",
        ge=1,
        le=50,
    )
    offset: int = Field(
        default=0,
        description="Offset für Paginierung.",
        ge=0,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' (lesbar) oder 'json' (maschinenlesbar).",
    )

    @model_validator(mode="after")
    def _validate_filters(self) -> SearchInput:
        if not any([self.query, self.domain, self.organization, self.bbox]):
            raise ValueError(
                "Mindestens einer von query/domain/organization/bbox muss gesetzt sein."
            )
        if self.bbox is not None:
            min_lon, min_lat, max_lon, max_lat = self.bbox
            if not -180 <= min_lon <= 180 or not -180 <= max_lon <= 180:
                raise ValueError("Longitude muss im Bereich [-180, 180] liegen.")
            if not -90 <= min_lat <= 90 or not -90 <= max_lat <= 90:
                raise ValueError("Latitude muss im Bereich [-90, 90] liegen.")
            if max_lon <= min_lon:
                raise ValueError("bbox: max_lon muss grösser als min_lon sein.")
            if max_lat <= min_lat:
                raise ValueError("bbox: max_lat muss grösser als min_lat sein.")
        return self


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


# ─── Ausgabe-Modelle (Spec 2026-07-28) ───────────────────────────────────────

# Warum es diese Modelle gibt, und warum ihre Felder nicht neu erfunden sind:
#
# Spec 2026-07-28 gibt einem Tool-Resultat ZWEI Kanaele — `content` fuer den
# Leser (Mensch oder Modell) und `structuredContent` fuer die Anwendung, mit
# `outputSchema` als Vertrag darueber. Dieser Server bediente bisher nur den
# ersten. Das SDK fuellte den zweiten trotzdem: eine Signatur `-> str` erzeugt
# ein Wrapper-Schema `{"result": string}` und legt denselben Markdown-Block ein
# zweites Mal darunter. Gemessen an `wsl_search` gegen die aufgezeichnete
# Antwort: 2058 Zeichen Text, 2058 Zeichen `structuredContent.result`,
# zeichengleich, 4393 Zeichen Gesamtnutzlast.
#
# Das ist schlechter als gar kein Schema. Ein `outputSchema` ist eine Zusage;
# diese hier verspricht Struktur und liefert Prosa unter einem Schluessel
# namens `result`. Eine Anwendung, die dem Vertrag glaubt und `structuredContent`
# liest statt `content` zu parsen, hat am Ende denselben Markdown-String — nur
# ueber einen Umweg, der wie eine Datenschnittstelle aussieht.
#
# Die Felder unten sind NICHT neu entworfen. Sie sind exakt die Nutzlast, die
# der `response_format="json"`-Zweig seit jeher erzeugt — dieselben Namen,
# dieselbe Reihenfolge, dieselben Typen. Dieser Zweig ist der Vorlaeufer von
# `structuredContent`: Er existiert nur, weil es vor 2026-07-28 keinen zweiten
# Kanal gab und man die maschinenlesbare Fassung deshalb als JSON-*String* in
# den Lesekanal legen musste. Nativ heisst hier also nicht «eine neue
# Schnittstelle», sondern: dieselbe Nutzlast in den Kanal, der fuer sie da ist.
#
# `response_format` bleibt, was es war, und steuert weiterhin nur den
# TEXT-Block. Es ist fuer maschinelle Leser jetzt entbehrlich — aber es zu
# entfernen waere ein Bruch an einer Stelle, an der niemand danach gefragt hat.


def _utc_now() -> str:
    """Der Abrufzeitpunkt, als eigener Modul-Alias.

    Nicht `datetime.now(...)` direkt im `default_factory`: Ein Test, der den
    doppelten Aufbau einer Nutzlast nachweisen will, braucht eine Uhr, die er
    steuern kann — und `monkeypatch.setattr(server.datetime, ...)` griffe ins
    fremde Modul `datetime` und entschaerfte es im ganzen Prozess. Der Alias
    hier ist unser eigener und laesst sich ersetzen, ohne etwas anderes zu
    beruehren.

    Dass es ihn braucht, hat die Gegenprobe gezeigt: Die Zusicherung «Text und
    Struktur nennen denselben Abrufzeitpunkt» blieb gruen, als der Aufbau
    absichtlich verdoppelt wurde — beide Aufbauten fielen in dieselbe Sekunde.
    Ein Test, der seinen eigenen Gegenstand nicht widerlegen kann, ist keine
    Zusicherung, sondern sieht nur aus wie eine.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Attribution(BaseModel):
    """CH-004: Quelle, Lizenz, Herkunftsart und Abrufzeit an jedem Resultat.

    Als Basisklasse und nicht als verschachteltes Objekt, damit die vier Felder
    im `structuredContent` dort stehen, wo sie im bisherigen JSON standen —
    zuoberst und flach. Eine Verschachtelung waere sauberer und haette den
    bestehenden Vertrag gebrochen.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        default="EnviDat / WSL (envidat.ch)",
        description="Datenquelle dieses Resultats.",
    )
    license: str = Field(
        default="various open licenses per dataset — see metadata",
        description="Lizenzlage; die genaue Lizenz steht je Datensatz.",
    )
    provenance: str = Field(
        default="live_api",
        description="Herkunftsart: 'live_api' = direkt bei der Quelle abgefragt.",
    )
    retrieved_at: str = Field(
        default_factory=lambda: _utc_now(),
        description="Abrufzeitpunkt (UTC, ISO 8601).",
    )


class DatasetSummary(BaseModel):
    """Ein Datensatz in Listenform — die neun Felder des bisherigen JSON."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, description="Slug (URL-Name) des Datensatzes.")
    title: Optional[str] = Field(default=None, description="Titel des Datensatzes.")
    notes: str = Field(default="", description="Beschreibung, auf 300 Zeichen gekuerzt.")
    modified: str = Field(default="", description="Letzte Aenderung (YYYY-MM-DD).")
    org: Optional[str] = Field(default=None, description="Slug der Forschungseinheit.")
    license: Optional[str] = Field(default=None, description="Lizenz dieses Datensatzes.")
    tags: list[str] = Field(default_factory=list, description="Schlagwoerter.")
    resources: int = Field(default=0, description="Anzahl herunterladbarer Ressourcen.")
    url: str = Field(default="", description="Permalink auf dem EnviDat-Portal.")


class SearchOutput(Attribution):
    """Resultat aller listenliefernden Such-Tools."""

    total_found: int = Field(default=0, description="Gesamtzahl der Treffer in der Quelle.")
    shown: int = Field(default=0, description="Davon in diesem Resultat enthalten.")
    datasets: list[DatasetSummary] = Field(default_factory=list, description="Die Treffer.")
    suggested_tags: list[str] = Field(
        default_factory=list,
        description=(
            "ARCH-003: verwandte Tags bei leerem Resultat. Im Textkanal stehen sie "
            "seit jeher als Prosa; hier stehen sie als Liste."
        ),
    )


class ResourceEntry(BaseModel):
    """Eine herunterladbare Datei eines Datensatzes."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, description="Dateiname oder Bezeichnung.")
    format: Optional[str] = Field(default=None, description="Format, z.B. CSV, NetCDF.")
    url: Optional[str] = Field(default=None, description="Direkter Download-Link.")
    size: Optional[int] = Field(default=None, description="Groesse in Bytes, wenn bekannt.")
    description: str = Field(default="", description="Beschreibung der Datei.")


class DatasetDetail(Attribution):
    """Die kuratierten Detailfelder eines Datensatzes.

    Bewusst NICHT das rohe CKAN-Paket: Dessen 42 Felder haben kein stabiles
    Schema, und ein `outputSchema` darueber waere wieder eine Zusage, die
    niemand halten kann. Wer alle Rohfelder braucht, bekommt sie unveraendert
    ueber `response_format="json"` im Textkanal — dieser Weg wird hier nicht
    angetastet, damit niemand Daten verliert, die er heute schon abholt.
    """

    name: Optional[str] = Field(default=None, description="Slug (URL-Name).")
    title: Optional[str] = Field(default=None, description="Titel.")
    notes: str = Field(default="", description="Vollstaendige Beschreibung.")
    org: Optional[str] = Field(default=None, description="Titel der Forschungseinheit.")
    created: str = Field(default="", description="Erstellt (YYYY-MM-DD).")
    modified: str = Field(default="", description="Letzte Aenderung (YYYY-MM-DD).")
    license: Optional[str] = Field(default=None, description="Lizenz.")
    doi: Optional[str] = Field(default=None, description="DOI ohne Praefix, wenn vergeben.")
    authors: Optional[str] = Field(default=None, description="Autorenangabe der Quelle.")
    publication_year: Optional[str] = Field(default=None, description="Publikationsjahr.")
    tags: list[str] = Field(default_factory=list, description="Schlagwoerter.")
    spatial: Optional[str] = Field(
        default=None,
        description="Raeumliche Ausdehnung, GeoJSON als String wie von der Quelle geliefert.",
    )
    resources: list[ResourceEntry] = Field(
        default_factory=list, description="Herunterladbare Dateien."
    )
    url: str = Field(default="", description="Permalink auf dem EnviDat-Portal.")


class OrganizationSummary(BaseModel):
    """Eine WSL-Forschungseinheit in Listenform."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, description="Slug der Einheit.")
    title: Optional[str] = Field(default=None, description="Ausgeschriebener Name.")
    description: str = Field(default="", description="Kurzbeschreibung.")
    package_count: int = Field(default=0, description="Anzahl publizierter Datensaetze.")


class OrganizationListOutput(Attribution):
    """Resultat von `wsl_list_organizations`."""

    total: int = Field(default=0, description="Anzahl Forschungseinheiten.")
    organizations: list[OrganizationSummary] = Field(
        default_factory=list, description="Die Einheiten, nach Datensatzzahl absteigend."
    )


class DatasetRef(BaseModel):
    """Ein Datensatz-Verweis innerhalb einer Organisation."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, description="Slug.")
    title: Optional[str] = Field(default=None, description="Titel.")
    modified: str = Field(default="", description="Letzte Aenderung (YYYY-MM-DD).")
    url: str = Field(default="", description="Permalink.")


class OrganizationDetail(Attribution):
    """Resultat von `wsl_get_organization`."""

    name: Optional[str] = Field(default=None, description="Slug der Einheit.")
    title: Optional[str] = Field(default=None, description="Ausgeschriebener Name.")
    description: str = Field(default="", description="Beschreibung.")
    package_count: int = Field(default=0, description="Anzahl Datensaetze insgesamt.")
    datasets: list[DatasetRef] = Field(
        default_factory=list,
        description=(
            "Datensaetze der Einheit. Der Textkanal zeigt hoechstens zehn; hier "
            "steht, was die Quelle geliefert hat."
        ),
    )


class TagListOutput(Attribution):
    """Resultat von `wsl_list_tags`."""

    query: Optional[str] = Field(default=None, description="Das angefragte Praefix, falls gesetzt.")
    total: int = Field(default=0, description="Wie viele Tags die Quelle zurueckgab.")
    shown: int = Field(default=0, description="Davon nach `limit` enthalten.")
    tags: list[str] = Field(default_factory=list, description="Die Schlagwoerter.")


class DomainCount(BaseModel):
    """Naeherungswert fuer eine Forschungsdomaene."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Schluessel der Domaene, z.B. 'wald'.")
    label: str = Field(description="Anzeigename der Domaene.")
    count: int = Field(default=0, description="Treffer der kuratierten Domaenen-Query.")


class CatalogStats(Attribution):
    """Resultat von `wsl_catalog_stats`."""

    portal: str = Field(default="", description="URL des EnviDat-Portals.")
    total_datasets: int = Field(default=0, description="Datensaetze im Katalog.")
    organization_count: int = Field(default=0, description="Anzahl Forschungseinheiten.")
    domains: list[DomainCount] = Field(
        default_factory=list, description="Naeherungswerte je Domaene."
    )
    top_organizations: list[OrganizationSummary] = Field(
        default_factory=list, description="Die sechs groessten Einheiten."
    )


def _tool_result(text: str, payload: Attribution) -> CallToolResult:
    """Beide Kanaele aus einer Quelle: lesbarer Text und `structuredContent`.

    Das SDK reicht ein zurueckgegebenes `CallToolResult` unveraendert durch und
    validiert `structured_content` gegen das Modell aus der Rueckgabe-Annotation
    (`mcp/server/mcpserver/utilities/func_metadata.py::convert_result`). Ein
    Feld, das nicht ins Schema passt, faellt damit beim Aufruf auf — nicht erst
    beim Leser.
    """
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=payload.model_dump(mode="json"),
    )


# ─── Hilfsfunktion: Suchergebnisse formatieren ───────────────────────────────


async def _suggest_tags(seed: str | None, *, limit: int = 5) -> list[str]:
    """Liefert verwandte Tags für leere Suchergebnisse (ARCH-003).

    Nimmt das erste Wort der ursprünglichen Query als Tag-Prefix.
    Wenn das fehlschlägt oder zu wenige Treffer kommen, gibt eine
    leere Liste zurück — die Suggestion ist Best-Effort, kein Pflicht.
    """
    if not seed:
        return []
    prefix = seed.split()[0][:8].strip().lower()
    if not prefix:
        return []
    try:
        tags = await ckan_tag_list(query=prefix)
    except Exception:
        return []
    return list(tags or [])[:limit]


def _as_int(value: Any) -> Optional[int]:
    """CKAN fuehrt `size` mal als Zahl, mal als Zeichenkette, mal gar nicht.

    Ohne diese Umwandlung entschiede die Schreibweise der Quelle darueber, ob
    der Aufruf gelingt: Ein `"12 KB"` im Feld liesse die Modellvalidierung den
    ganzen Datensatz verwerfen. Unlesbares wird `None` — das Feld ist optional
    und sagt dann, was es weiss, naemlich nichts.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dataset_detail_payload(pkg: dict[str, Any]) -> DatasetDetail:
    """Die kuratierten Detailfelder eines CKAN-Pakets.

    Spiegelt die Felder, die der Markdown-Zweig unten anzeigt. Wer das rohe
    Paket braucht, holt es weiterhin unveraendert ueber
    `response_format="json"` aus dem Textkanal.
    """
    extras = {e.get("key"): e.get("value") for e in pkg.get("extras", [])}
    name = pkg.get("name")
    return DatasetDetail(
        name=name,
        title=pkg.get("title"),
        notes=pkg.get("notes") or "",
        org=(pkg.get("organization") or {}).get("title"),
        created=pkg.get("metadata_created", "")[:10],
        modified=pkg.get("metadata_modified", "")[:10],
        license=pkg.get("license_title"),
        doi=pkg.get("doi") or pkg.get("extras_doi") or None,
        authors=extras.get("authors") or extras.get("author") or None,
        publication_year=extras.get("publication_year") or None,
        tags=[str(t.get("name")) for t in pkg.get("tags", []) if t.get("name")],
        spatial=extras.get("spatial") or None,
        resources=[
            ResourceEntry(
                name=r.get("name") or r.get("id"),
                format=(r.get("format") or None),
                url=r.get("url"),
                size=_as_int(r.get("size")),
                description=r.get("description") or "",
            )
            for r in pkg.get("resources", [])
        ],
        url=f"{ENVIDAT_PORTAL}/dataset/{name}",
    )


def _organization_summary(org: dict[str, Any]) -> OrganizationSummary:
    """Eine Forschungseinheit in Listenform — an zwei Stellen gebraucht."""
    return OrganizationSummary(
        name=org.get("name"),
        title=org.get("title") or org.get("name"),
        description=org.get("description") or "",
        package_count=org.get("package_count", 0) or 0,
    )


def _search_payload(
    result: dict[str, Any],
    suggestions: list[str] | None = None,
) -> SearchOutput:
    """Baut die maschinenlesbare Fassung eines Suchresultats.

    Die einzige Stelle, an der CKAN-Pakete auf unsere Felder abgebildet werden.
    Sowohl `structuredContent` als auch der `response_format="json"`-Textzweig
    gehen hier durch — zwei Abbildungen waeren zwei Wahrheiten.
    """
    packages = ckan_results(result)
    return SearchOutput(
        total_found=result.get("count", 0),
        shown=len(packages),
        datasets=[
            DatasetSummary(
                name=p.get("name"),
                title=p.get("title"),
                notes=(p.get("notes") or "")[:300],
                modified=p.get("metadata_modified", "")[:10],
                org=(p.get("organization") or {}).get("name"),
                license=p.get("license_title"),
                # Namenlose Tags fallen raus statt als `None` in einer
                # `list[str]` zu landen. Ein Tag ohne Namen traegt nichts, und
                # ein `None` darin liesse die Modellvalidierung den ganzen
                # Aufruf abbrechen — ein kosmetischer Mangel der Quelle wuerde
                # so zum Ausfall des Werkzeugs.
                tags=[str(t.get("name")) for t in p.get("tags", []) if t.get("name")],
                resources=len(p.get("resources", [])),
                url=f"{ENVIDAT_PORTAL}/dataset/{p.get('name')}",
            )
            for p in packages
        ],
        suggested_tags=list(suggestions or []),
    )


def _search_result(
    result: dict[str, Any],
    response_format: ResponseFormat,
    title: str = "EnviDat Suchergebnisse",
    suggestions: list[str] | None = None,
) -> CallToolResult:
    """Text und `structuredContent` eines Suchresultats, aus einem Aufbau.

    Die fuenf listenliefernden Tools gehen hier durch. Frueher endete jedes in
    einem `return _format_search_results(...)` — einem String, den das SDK dann
    unter `{"result": ...}` ein zweites Mal als angeblich strukturierte Ausgabe
    beilegte.
    """
    payload = _search_payload(result, suggestions)
    text = _format_search_results(
        result,
        response_format,
        title=title,
        suggestions=suggestions,
        payload=payload,
    )
    return _tool_result(text, payload)


def _format_search_results(
    result: dict[str, Any],
    response_format: ResponseFormat,
    title: str = "EnviDat Suchergebnisse",
    suggestions: list[str] | None = None,
    payload: SearchOutput | None = None,
) -> str:
    """Formatiert Suchergebnisse einheitlich für alle Such-Tools.

    `payload` ist die bereits gebaute Nutzlast. Sie wird durchgereicht statt
    ein zweites Mal erzeugt: `retrieved_at` steht sonst im Textkanal auf einer
    anderen Sekunde als in `structuredContent`, und eine Antwort, die sich
    selbst zwei Abrufzeiten gibt, ist in genau dem Punkt unglaubwuerdig, den
    das Feld belegen soll.
    """
    packages = ckan_results(result)
    count = result.get("count", 0)
    shown = len(packages)

    if response_format == ResponseFormat.JSON:
        # Dieselbe Nutzlast wie `structuredContent`, nur serialisiert: sonst
        # gaebe es zwei Fassungen derselben Antwort, die auseinanderlaufen
        # koennen, ohne dass ein Test das bemerkt.
        payload = payload if payload is not None else _search_payload(result, suggestions)
        return payload.model_dump_json(indent=2)

    if not packages:
        msg = "Keine Datensätze gefunden. Bitte Suchbegriff anpassen."
        if suggestions:
            hints = ", ".join(f"`{t}`" for t in suggestions)
            msg += (
                f"\n\n**Mögliche verwandte Tags:** {hints}"
                "\n\n_Hinweis: Mit `wsl_list_tags` lassen sich weitere Tags durchsuchen._"
            )
        return msg

    lines = [f"## {title}", f"**{count} Datensätze gefunden** (zeige {shown}):\n"]
    for i, pkg in enumerate(packages, 1):
        lines.append(f"---\n**{i}.** {format_dataset_summary(pkg, include_resources=False)}")

    lines.append(
        f"\n---\n*Alle Datensätze auf [EnviDat]({ENVIDAT_PORTAL}) · "
        "API: https://www.envidat.ch/api/action/*"
    )
    return "\n".join(lines)


# ─── Tool 1: Unifizierte Suche ────────────────────────────────────────────────


@mcp.tool(
    name="wsl_search",
    description=(
        "Unifizierte Suche im EnviDat-Katalog der WSL (Eidg. Forschungsanstalt "
        "für Wald, Schnee und Landschaft). Kombiniert frei wählbar Stichwort, "
        "kuratierte Forschungsdomäne, Organisation und Bounding-Box.\n\n"
        "<use_case>Schweizer Umweltforschung, Schulhaus-Umgebungsanalysen, "
        "Klimafolgen-Recherche, kantonale Umweltberichte, Lawinendaten, "
        "Waldzustand, Biodiversität, Naturgefahren.</use_case>\n\n"
        "<important_notes>Mindestens einer der Filter (query/domain/"
        "organization/bbox) muss gesetzt sein. Solr-Syntax ist möglich, "
        "'OR' ist aber Stopwort. Bei leerem Resultat liefert das Tool "
        "verwandte Tags als Vorschlag.</important_notes>\n\n"
        "<example>query='snow avalanche' → SLF-Lawinendaten. "
        "domain='wald' → kuratierte LFI-/Sanasilva-Suche. "
        "bbox=[8.35,47.15,8.98,47.72] → Kanton Zürich. "
        "query='forest', organization='wsl' → WSL-Walddatensätze.</example>"
    ),
    title="EnviDat Suche",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_search(params: SearchInput) -> Annotated[CallToolResult, SearchOutput]:
    """Unifizierte Suche im EnviDat-Katalog.

    Ersetzt seit v0.2.0 die drei separaten Such-Tools `wsl_search_datasets`,
    `wsl_search_by_domain` und `wsl_search_by_location` (ARCH-006).

    Args:
        params (SearchInput): Filter — mindestens einer von query / domain /
            organization / bbox muss gesetzt sein. Plus limit, offset und
            response_format.

    Returns:
        CallToolResult: Markdown oder JSON im Textkanal, dazu die Treffer als
            `structuredContent` nach `SearchOutput` — inkl. Tag-Suggestions bei
            leerem Resultat.
    """
    try:
        # Effektive Query: explizite query > domain-Keyword > Wildcard
        if params.query:
            query = params.query
        elif params.domain:
            query = build_domain_query(params.domain.value)
        else:
            query = "*:*"

        fq = f"organization:{params.organization}" if params.organization else ""
        extras: dict[str, Any] | None = None
        if params.bbox is not None:
            extras = {"ext_bbox": ",".join(str(c) for c in params.bbox)}

        result = await ckan_package_search(
            query=query,
            fq=fq,
            rows=params.limit,
            start=params.offset,
            extras=extras,
        )

        # ARCH-003: Bei leerem Resultat best-effort Tag-Suggestion liefern.
        suggestions: list[str] | None = None
        if not result.get("results") and (params.query or params.domain):
            suggestions = await _suggest_tags(
                params.query or (params.domain.value if params.domain else None)
            )

        title = _search_title(params)
        return _search_result(
            result,
            params.response_format,
            title=title,
            suggestions=suggestions,
        )
    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_search")) from e


def _search_title(params: SearchInput) -> str:
    """Baut einen lesbaren Markdown-Titel für die Suche."""
    parts: list[str] = []
    if params.query:
        parts.append(f"«{params.query}»")
    if params.domain:
        label = {
            "wald": "🌲 Wald",
            "biodiversitaet": "🦋 Biodiversität",
            "naturgefahren": "⛰️ Naturgefahren",
            "schnee_eis": "❄️ Schnee & Eis",
            "landschaft": "🏞️ Landschaft",
        }.get(params.domain.value, params.domain.value)
        parts.append(f"Domäne {label}")
    if params.organization:
        parts.append(f"Organisation `{params.organization}`")
    if params.bbox is not None:
        b = params.bbox
        parts.append(f"BBox [{b[0]:.2f},{b[1]:.2f} → {b[2]:.2f},{b[3]:.2f}]")
    return "Suchergebnisse — " + ", ".join(parts) if parts else "EnviDat Suchergebnisse"


# ─── Tool 2: Datensatz-Details ────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_dataset",
    description=(
        "Gibt vollständige Metadaten und Ressourcen (Download-URLs) eines "
        "EnviDat-Datensatzes zurück.\n\n"
        "<use_case>Detail-Ansicht eines konkreten Datensatzes mit DOI, "
        "Lizenz, Autoren, Download-Links und räumlicher Ausdehnung. "
        "Folge-Schritt nach wsl_search.</use_case>\n\n"
        "<important_notes>id_or_slug ist entweder die UUID oder der URL-Slug "
        "aus dem Suchergebnis (Feld 'name'). Liefert auch nicht-öffentliche "
        "Resource-Metadaten wenn vorhanden.</important_notes>\n\n"
        "<example>id_or_slug='fatal-avalanche-accidents-in-switzerland-since-1936-37' "
        "→ vollständige Lawinen-Datenbankbeschreibung mit CSV-Download-Link.</example>"
    ),
    title="EnviDat Datensatz-Details",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_dataset(params: GetDatasetInput) -> Annotated[CallToolResult, DatasetDetail]:
    """Gibt vollständige Metadaten und Ressourcen (Download-URLs) eines EnviDat-Datensatzes zurück.

    Liefert Titel, Beschreibung, Autoren, Zeitraum, Räumliche Ausdehnung, DOI,
    Lizenz, alle Ressourcen (Daten-Downloads) und Projektinformationen.

    Args:
        params (GetDatasetInput): Mit:
            - id_or_slug (str): Dataset-ID (UUID) oder URL-Slug
            - response_format: 'markdown' oder 'json'

    Returns:
        CallToolResult: Markdown oder das rohe CKAN-Paket im Textkanal, dazu
            die kuratierten Felder als `structuredContent` nach `DatasetDetail`.
    """
    try:
        pkg = await ckan_package_show(params.id_or_slug)
        payload = _dataset_detail_payload(pkg)

        if params.response_format == ResponseFormat.JSON:
            # Bewusst weiterhin das ROHE Paket, nicht die kuratierte Fassung:
            # Wer diesen Zweig heute abholt, bekommt 42 Felder. Ihn auf die
            # kuratierten zu verengen, hiesse Daten wegzunehmen, um ein Schema
            # zu gewinnen — und niemand hat danach gefragt.
            return _tool_result(json.dumps(pkg, indent=2, ensure_ascii=False), payload)

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
        return _tool_result("\n".join(lines), payload)

    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_get_dataset")) from e


# ─── Tool 5: Organisationen auflisten ─────────────────────────────────────────


@mcp.tool(
    name="wsl_list_organizations",
    title="WSL-Forschungseinheiten auflisten",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_list_organizations() -> Annotated[CallToolResult, OrganizationListOutput]:
    """Listet alle WSL-Forschungseinheiten und deren Datensatz-Anzahl auf.

    Gibt einen Überblick über die Forschungsgruppen der WSL, die Daten auf
    EnviDat publiziert haben. Nützlich zur Identifikation relevanter
    Organisationen für nachfolgende Abfragen mit wsl_get_organization.

    Returns:
        CallToolResult: Lesbare Liste im Textkanal, dazu die Einheiten als
            `structuredContent` nach `OrganizationListOutput`.
    """
    try:
        orgs = await ckan_organization_list(all_fields=True)
        ranked = sorted(orgs, key=lambda x: x.get("package_count", 0), reverse=True)
        payload = OrganizationListOutput(
            total=len(orgs),
            organizations=[_organization_summary(o) for o in ranked],
        )

        if not orgs:
            # Auch die Leermenge traegt ihre Struktur: ein Client, der
            # `structuredContent` liest, bekommt `total: 0` statt gar nichts
            # und muss den Satz nicht auslegen.
            return _tool_result("Keine Organisationen gefunden.", payload)

        lines = [
            "## WSL-Forschungseinheiten auf EnviDat\n",
            f"**{len(orgs)} Organisationen** mit Datensätzen:\n",
        ]
        for org in ranked:
            name = org.get("name", "–")
            title = org.get("title") or name
            count = org.get("package_count", 0)
            desc = (org.get("description") or "")[:120]
            lines.append(f"- **{title}** (`{name}`) – {count} Datensätze")
            if desc:
                lines.append(f"  _{desc}_")

        lines.append("\n*Tipp: `wsl_get_organization` für Details zu einer Einheit*")
        return _tool_result("\n".join(lines), payload)

    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_list_organizations")) from e


# ─── Tool 6: Organisation-Details ─────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_organization",
    title="WSL-Forschungseinheit Details",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_get_organization(
    params: GetOrganizationInput,
) -> Annotated[CallToolResult, OrganizationDetail]:
    """Gibt Details einer WSL-Forschungseinheit inklusive ihrer Datensätze zurück.

    Liefert Beschreibung, Kontakt und Datensatz-Übersicht einer Organisation.
    Das SLF (Institut für Schnee- und Lawinenforschung) ist als 'slf' abrufbar.

    Args:
        params (GetOrganizationInput): Mit:
            - name (str): Organisations-Slug (z.B. 'wsl', 'slf')
            - include_datasets (bool): Datensätze mitausgeben

    Returns:
        CallToolResult: Lesbare Details im Textkanal, dazu die Einheit als
            `structuredContent` nach `OrganizationDetail`.
    """
    try:
        org = await ckan_organization_show(params.name, params.include_datasets)

        title = org.get("title") or org.get("name", "–")
        name = org.get("name", "–")
        desc = org.get("description") or "Keine Beschreibung."
        count = org.get("package_count", 0)
        pkgs = org.get("packages", [])

        payload = OrganizationDetail(
            name=org.get("name"),
            title=org.get("title") or org.get("name"),
            description=org.get("description") or "",
            package_count=count,
            # Der Textkanal zeigt hoechstens zehn Datensaetze. Hier stehen
            # alle, die die Quelle geliefert hat: die Kuerzung ist eine
            # Lesbarkeitsentscheidung und keine Aussage ueber den Bestand.
            datasets=[
                DatasetRef(
                    name=pkg.get("name"),
                    title=pkg.get("title") or pkg.get("name"),
                    modified=pkg.get("metadata_modified", "")[:10],
                    url=f"{ENVIDAT_PORTAL}/dataset/{pkg.get('name')}",
                )
                for pkg in pkgs
            ],
        )

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

        return _tool_result("\n".join(lines), payload)

    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_get_organization")) from e


# ─── Tool 7: Tags auflisten ───────────────────────────────────────────────────


@mcp.tool(
    name="wsl_list_tags",
    title="EnviDat Tags/Schlagwörter auflisten",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_list_tags(params: ListTagsInput) -> Annotated[CallToolResult, TagListOutput]:
    """Listet verfügbare Schlagwörter (Tags) im EnviDat-Katalog auf.

    Nützlich um herauszufinden, welche Suchbegriffe in wsl_search
    präzise Ergebnisse liefern. Unterstützt Präfix-Suche.

    Args:
        params (ListTagsInput): Mit:
            - query (str): Optionaler Suchbegriff für Tags
            - limit (int): Maximale Anzahl Tags

    Returns:
        CallToolResult: Lesbare Tag-Liste im Textkanal, dazu die Tags als
            `structuredContent` nach `TagListOutput`.
    """
    try:
        tags = await ckan_tag_list(query=params.query or "")
        filtered = tags[: params.limit]

        payload = TagListOutput(
            query=params.query,
            # `total` ist, was die Quelle zurueckgab, `shown` das nach `limit`
            # Verbliebene. Nur `shown` zu melden liesse einen Aufrufer glauben,
            # er habe alles — derselbe Fehler wie eine Trefferzahl, die die
            # Seitengroesse meldet.
            total=len(tags),
            shown=len(filtered),
            tags=list(filtered),
        )

        prefix = f"«{params.query}»" if params.query else "alle"
        text = f"## EnviDat Tags ({prefix})\n\n{len(filtered)} Tags gefunden:\n\n" + ", ".join(
            f"`{t}`" for t in filtered
        )
        return _tool_result(text, payload)
    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_list_tags")) from e


# ─── Tool 8: Aktuelle Datensätze ──────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_recent_datasets",
    title="Neuste EnviDat Datensätze",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def wsl_get_recent_datasets(
    params: GetRecentDatasetsInput,
) -> Annotated[CallToolResult, SearchOutput]:
    """Gibt die zuletzt publizierten oder aktualisierten EnviDat-Datensätze zurück.

    Nützlich für regelmässige Monitoring-Workflows und um neue WSL-Forschungsdaten
    zu entdecken.

    Args:
        params (GetRecentDatasetsInput): Mit limit und response_format

    Returns:
        CallToolResult: Zuletzt aktualisierte Datensätze
    """
    try:
        result = await ckan_package_search(
            query="*:*",
            rows=params.limit,
            sort="metadata_modified desc",
        )
        return _search_result(
            result,
            params.response_format,
            title="Zuletzt aktualisierte WSL-Datensätze",
        )
    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_get_recent_datasets")) from e


# ─── Tool 9: Lawinendaten ─────────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_avalanche_data",
    title="SLF Lawinen- & Schneedaten",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_avalanche_data(
    params: SimpleQueryInput,
) -> Annotated[CallToolResult, SearchOutput]:
    """Lawinen- und Schneedaten vom WSL-Institut fuer Schnee- und Lawinenforschung (SLF).

    Enthält u.a.:
    - Tödliche Lawinenunfälle in der Schweiz seit 1936/37
    - Langjährige Schneemessreihen (Station Stillberg Davos, 2090 m)
    - Meteorologische Langzeitdaten Hochgebirge
    - Schneephysik-Forschungsdaten

    Args:
        params (SimpleQueryInput): Anzahl Ergebnisse und Format

    Returns:
        CallToolResult: Lawinen- und Schneedatensätze des SLF
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
        return _search_result(
            result,
            params.response_format,
            title="❄️ SLF Lawinen- & Schneedaten",
        )
    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_get_avalanche_data")) from e


# ─── Tool 10: Walddaten ───────────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_forest_data",
    title="WSL Walddaten & Forstinventar",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_forest_data(params: SimpleQueryInput) -> Annotated[CallToolResult, SearchOutput]:
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
        CallToolResult: Walddatensätze der WSL
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
        return _search_result(
            result,
            params.response_format,
            title="🌲 Walddaten & Forstinventar (LFI)",
        )
    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_get_forest_data")) from e


# ─── Tool 11: Naturgefahren ───────────────────────────────────────────────────


@mcp.tool(
    name="wsl_get_naturgefahren_data",
    title="WSL Naturgefahren-Daten",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wsl_get_naturgefahren_data(
    params: SimpleQueryInput,
) -> Annotated[CallToolResult, SearchOutput]:
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
        CallToolResult: Naturgefahren-Datensätze der WSL
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
        return _search_result(
            result,
            params.response_format,
            title="⛰️ Naturgefahren-Daten der WSL",
        )
    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_get_naturgefahren_data")) from e


# ─── Tool 12: Katalog-Statistiken ─────────────────────────────────────────────


@mcp.tool(
    name="wsl_catalog_stats",
    title="EnviDat Katalog-Übersicht",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def wsl_catalog_stats() -> Annotated[CallToolResult, CatalogStats]:
    """Gibt eine Übersicht über den EnviDat-Katalog zurück: Domänen, Organisationen, Datenmenge.

    Nützlich als Einstiegspunkt: zeigt was im Katalog verfügbar ist,
    welche WSL-Forschungsdomänen besonders viele Datensätze haben,
    und wie der Katalog strukturiert ist.

    Returns:
        CallToolResult: Lesbare Uebersicht im Textkanal, dazu die Zahlen als
            `structuredContent` nach `CatalogStats`.
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
        payload = CatalogStats(
            portal=ENVIDAT_PORTAL,
            total_datasets=total,
            organization_count=num_orgs,
            # Die Zahlen im Textkanal tragen ein «~» und heissen dort
            # ausdruecklich Naeherungswerte: sie zaehlen die Treffer einer
            # kuratierten Domaenen-Query, nicht eine Zuordnung der Quelle.
            # Das Modell kann diese Einschraenkung nicht mitfuehren, das
            # Feld heisst deshalb schlicht `count` — die Beschreibung im
            # Schema sagt, woher er kommt.
            domains=[
                DomainCount(
                    domain=key,
                    label=label,
                    count=domain_counts.get(key, 0),
                )
                for key, label in domain_labels.items()
            ],
            top_organizations=[_organization_summary(o) for o in top_orgs],
        )
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

        return _tool_result("\n".join(lines), payload)

    except Exception as e:
        raise ToolError(handle_api_error(e, "wsl_catalog_stats")) from e


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
        # Resource-Errors propagieren als JSON-RPC-Fehler (statt als
        # "erfolgreiche" Resource-Read mit Error-Payload).
        raise RuntimeError(handle_api_error(e, "envidat://organization")) from e


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
                    for p in ckan_results(result)
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        raise RuntimeError(handle_api_error(e, "envidat://domain")) from e


# ─── Entry point ──────────────────────────────────────────────────────────────


def build_transport_security(host: str, port: int):
    """Host/Origin allow-list for the HTTP transport (SEC-005, inbound half).

    The SDK leaves DNS-rebinding protection OFF while ``transport_security`` is
    unset — its own source says "If not specified, disable DNS rebinding
    protection by default for backwards compatibility". Unset therefore means
    no Host and no Origin validation at all.

    Returns ``None`` when no allow-list can be derived: a non-loopback bind with
    no ``MCP_ALLOWED_HOSTS``. The server is then reached under a service or
    public DNS name this process does not know, and a guessed list would reject
    every real request with HTTP 421. The caller warns instead.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    allowed = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    loopback = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    if allowed:
        # Loopback stays reachable for container health checks and debugging.
        hosts = set(allowed) | loopback
    elif host in ("127.0.0.1", "localhost", "::1"):
        hosts = loopback | {f"{host}:{port}"}
    else:
        return None

    origins = {f"http://{h}" for h in hosts}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(origins),
    )


def main() -> None:
    """Startet den WSL/EnviDat MCP Server."""
    import os

    # MCP-SDK akzeptiert "stdio" | "sse" | "streamable-http".
    # Wir akzeptieren auch die Underscore-Variante "streamable_http" für
    # Backward-Kompatibilität mit existierenden Claude-Desktop-Setups.
    transport = os.environ.get("MCP_TRANSPORT", "stdio").replace("_", "-")
    port = int(os.environ.get("PORT", "8000"))
    # SEC-016: lokaler Default 127.0.0.1 — 0.0.0.0 nur via expliziter
    # Env-Var (Container-Netzwerk-Isolation). Verhindert NeighborJack im
    # öffentlichen WLAN bei MCP_TRANSPORT=streamable-http.
    host = os.environ.get("MCP_HOST", "127.0.0.1")

    if LATEST_PROTOCOL_VERSION != SUPPORTED_MCP_PROTOCOL_VERSION:
        logger.warning(
            "mcp_protocol_version.drift",
            sdk_latest=LATEST_PROTOCOL_VERSION,
            tested_against=SUPPORTED_MCP_PROTOCOL_VERSION,
            hint="Run the MCP Inspector and bump SUPPORTED_MCP_PROTOCOL_VERSION",
        )

    if transport == "streamable-http":
        security = build_transport_security(host, port)
        if security is None:
            logger.warning(
                "dns_rebinding_protection_off",
                host=host,
                hint="Set MCP_ALLOWED_HOSTS to the hostnames this server is "
                "reachable under; without it the SDK does not check the Host "
                "header at all.",
            )
        logger.info(
            "server.start",
            transport="streamable-http",
            host=host,
            port=port,
            mcp_protocol_version=LATEST_PROTOCOL_VERSION,
        )
        # mcp 2.x: bind address and transport_security are run() kwargs;
        # MCPServer.settings no longer carries them.
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            transport_security=security,
        )
    else:
        logger.info(
            "server.start",
            transport="stdio",
            mcp_protocol_version=LATEST_PROTOCOL_VERSION,
        )
        mcp.run()


if __name__ == "__main__":
    main()
