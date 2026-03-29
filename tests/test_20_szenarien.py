"""20 diverse Testszenarien für den WSL/EnviDat MCP Server.

Testet alle 12 Tools, 2 Resources, Fehlerbehandlung, Validierung,
Formatierungsoptionen und Edge Cases gegen die Live EnviDat API.

Ausführen: python test_20_szenarien.py
Hinweis: Erfordert aktive Internetverbindung.
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path

# src/ ins sys.path aufnehmen
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsl_envidat_mcp.api_client import (
    build_domain_query,
    ckan_organization_list,
    ckan_organization_show,
    ckan_package_search,
    ckan_package_show,
    ckan_tag_list,
    ckan_status_show,
    format_dataset_summary,
    handle_api_error,
    DOMAIN_KEYWORDS,
    ENVIDAT_PORTAL,
)

from wsl_envidat_mcp.server import (
    _format_search_results,
    ResponseFormat,
    SearchDatasetsInput,
    GetDatasetInput,
    SearchByDomainInput,
    SearchByLocationInput,
    ListTagsInput,
    GetRecentDatasetsInput,
    SimpleQueryInput,
    GetOrganizationInput,
    WSLDomain,
    wsl_search_datasets,
    wsl_get_dataset,
    wsl_search_by_domain,
    wsl_search_by_location,
    wsl_list_organizations,
    wsl_get_organization,
    wsl_list_tags,
    wsl_get_recent_datasets,
    wsl_get_avalanche_data,
    wsl_get_forest_data,
    wsl_get_naturgefahren_data,
    wsl_catalog_stats,
    get_organization_resource,
    get_domain_resource,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 1: Volltextsuche mit JSON-Ausgabe
#  Prüft: wsl_search_datasets + response_format=json
# ═══════════════════════════════════════════════════════════════════════════════

async def test_01_search_json_format() -> None:
    """Szenario 1: Volltextsuche gibt valides JSON zurück."""
    params = SearchDatasetsInput(
        query="glacier monitoring",
        limit=3,
        response_format=ResponseFormat.JSON,
    )
    result = await wsl_search_datasets(params)
    data = json.loads(result)
    assert "total_found" in data, "JSON-Antwort fehlt 'total_found'"
    assert "datasets" in data, "JSON-Antwort fehlt 'datasets'"
    assert isinstance(data["datasets"], list)
    assert data["total_found"] > 0, "Keine Treffer für 'glacier monitoring'"
    for ds in data["datasets"]:
        assert "name" in ds and "title" in ds and "url" in ds
    print(f"  ✓ JSON: {data['total_found']} Treffer, {len(data['datasets'])} zurückgegeben")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 2: Suche mit Organisations-Filter
#  Prüft: wsl_search_datasets + organization-Filter
# ═══════════════════════════════════════════════════════════════════════════════

async def test_02_search_with_org_filter() -> None:
    """Szenario 2: Suche eingeschränkt auf eine bestimmte Organisation."""
    # Zuerst Organisationen holen
    orgs = await ckan_organization_list(all_fields=True)
    assert len(orgs) > 0
    first_org = orgs[0]["name"]

    params = SearchDatasetsInput(
        query="*:*",
        limit=5,
        organization=first_org,
    )
    result = await wsl_search_datasets(params)
    assert "Datensätze gefunden" in result or "total_found" in result
    print(f"  ✓ Org-Filter '{first_org}': Ergebnisse erhalten")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 3: Dataset-Details in Markdown
#  Prüft: wsl_get_dataset mit Markdown-Format (DOI, Ressourcen, Tags)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_03_dataset_details_markdown() -> None:
    """Szenario 3: Abruf vollständiger Dataset-Details in Markdown."""
    # Suche bekannten Datensatz
    search = await ckan_package_search(query="snow depth", rows=1)
    slug = search["results"][0]["name"]

    params = GetDatasetInput(id_or_slug=slug)
    result = await wsl_get_dataset(params)
    assert "# " in result, "Markdown-Überschrift fehlt"
    assert "Slug:" in result, "Slug-Angabe fehlt"
    assert "Organisation:" in result
    assert "EnviDat öffnen" in result, "Portal-Link fehlt"
    print(f"  ✓ Dataset-Details (MD): '{slug}' – {len(result)} Zeichen")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 4: Dataset-Details in JSON
#  Prüft: wsl_get_dataset + response_format=json
# ═══════════════════════════════════════════════════════════════════════════════

async def test_04_dataset_details_json() -> None:
    """Szenario 4: Dataset-Details als vollständiges JSON."""
    search = await ckan_package_search(query="forest inventory", rows=1)
    slug = search["results"][0]["name"]

    params = GetDatasetInput(id_or_slug=slug, response_format=ResponseFormat.JSON)
    result = await wsl_get_dataset(params)
    data = json.loads(result)
    assert "name" in data, "JSON fehlt 'name'"
    assert "resources" in data, "JSON fehlt 'resources'"
    assert data["name"] == slug
    print(f"  ✓ Dataset-Details (JSON): '{slug}' mit {len(data['resources'])} Ressourcen")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 5: Domänensuche – alle 5 Domänen nacheinander
#  Prüft: wsl_search_by_domain für jede WSLDomain
# ═══════════════════════════════════════════════════════════════════════════════

async def test_05_all_domains() -> None:
    """Szenario 5: Alle 5 Forschungsdomänen liefern Ergebnisse."""
    for domain in WSLDomain:
        params = SearchByDomainInput(domain=domain, limit=2)
        result = await wsl_search_by_domain(params)
        assert "Datensätze gefunden" in result, f"Domäne '{domain.value}' liefert keine Treffer"
    print(f"  ✓ Alle 5 Domänen liefern Ergebnisse")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 6: Domänensuche mit JSON-Format
#  Prüft: wsl_search_by_domain + JSON-Ausgabe
# ═══════════════════════════════════════════════════════════════════════════════

async def test_06_domain_json() -> None:
    """Szenario 6: Domänensuche in JSON-Format."""
    params = SearchByDomainInput(
        domain=WSLDomain.SCHNEE_EIS,
        limit=5,
        response_format=ResponseFormat.JSON,
    )
    result = await wsl_search_by_domain(params)
    data = json.loads(result)
    assert data["total_found"] > 0
    assert len(data["datasets"]) <= 5
    print(f"  ✓ Domäne 'schnee_eis' (JSON): {data['total_found']} Treffer")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 7: Räumliche Suche – Davos-Region
#  Prüft: wsl_search_by_location mit BBox um Davos
# ═══════════════════════════════════════════════════════════════════════════════

async def test_07_spatial_search_davos() -> None:
    """Szenario 7: Räumliche Suche in der Region Davos."""
    params = SearchByLocationInput(
        min_lon=9.7, min_lat=46.7,
        max_lon=10.0, max_lat=46.9,
        limit=5,
    )
    result = await wsl_search_by_location(params)
    # Bei 0 Treffern: "Keine Datensätze gefunden", sonst BBox im Titel
    assert "BBox" in result or "Keine Datensätze" in result, "Unerwartete Antwort"
    print(f"  ✓ Raeumliche Suche Davos: Antwort erhalten ({len(result)} Zeichen)")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 8: Räumliche Suche mit Suchbegriff
#  Prüft: wsl_search_by_location + zusätzlicher query-Parameter
# ═══════════════════════════════════════════════════════════════════════════════

async def test_08_spatial_search_with_query() -> None:
    """Szenario 8: Räumliche Suche kombiniert mit Suchbegriff."""
    params = SearchByLocationInput(
        min_lon=5.95, min_lat=45.8,
        max_lon=10.5, max_lat=47.8,
        query="permafrost",
        limit=5,
    )
    result = await wsl_search_by_location(params)
    assert "BBox" in result or "Keine Datensätze" in result, "Unerwartete Antwort"
    print(f"  ✓ Raeumliche Suche CH + 'permafrost': OK")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 9: Organisationen auflisten
#  Prüft: wsl_list_organizations Vollständigkeit
# ═══════════════════════════════════════════════════════════════════════════════

async def test_09_list_organizations() -> None:
    """Szenario 9: Alle WSL-Forschungseinheiten werden aufgelistet."""
    result = await wsl_list_organizations()
    assert "Organisationen" in result
    assert "Datensätze" in result
    # Prüfe dass Slugs in Backticks stehen (Markdown-Formatierung)
    assert "`" in result, "Slugs sollten in Backticks formatiert sein"
    print(f"  ✓ Organisationsliste: {len(result)} Zeichen")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 10: Organisation-Details mit Datensätzen
#  Prüft: wsl_get_organization mit include_datasets=True
# ═══════════════════════════════════════════════════════════════════════════════

async def test_10_organization_details() -> None:
    """Szenario 10: Details einer Organisation inkl. Datensätze."""
    # Hole die erste Organisation
    orgs = await ckan_organization_list(all_fields=True)
    org_slug = orgs[0]["name"]

    params = GetOrganizationInput(name=org_slug, include_datasets=True)
    result = await wsl_get_organization(params)
    assert "## " in result, "Markdown-Überschrift fehlt"
    assert "Datensätze" in result
    print(f"  ✓ Organisation '{org_slug}': Details mit Datensätzen")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 11: Tags nach Präfix filtern
#  Prüft: wsl_list_tags mit query-Parameter
# ═══════════════════════════════════════════════════════════════════════════════

async def test_11_tags_with_prefix() -> None:
    """Szenario 11: Tags nach Präfix filtern (z.B. 'forest')."""
    params = ListTagsInput(query="forest", limit=20)
    result = await wsl_list_tags(params)
    assert "Tags" in result
    assert "`" in result, "Tags sollten als Code formatiert sein"
    print(f"  ✓ Tags mit Präfix 'forest': gefunden")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 12: Neueste Datensätze
#  Prüft: wsl_get_recent_datasets Sortierung und Inhalte
# ═══════════════════════════════════════════════════════════════════════════════

async def test_12_recent_datasets() -> None:
    """Szenario 12: Zuletzt aktualisierte Datensätze abrufen."""
    params = GetRecentDatasetsInput(limit=5, response_format=ResponseFormat.MARKDOWN)
    result = await wsl_get_recent_datasets(params)
    assert "Zuletzt aktualisierte" in result
    assert "Datensätze gefunden" in result
    print(f"  ✓ Neueste Datensätze (5): OK")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 13: Lawinendaten (SLF)
#  Prüft: wsl_get_avalanche_data Spezial-Tool
# ═══════════════════════════════════════════════════════════════════════════════

async def test_13_avalanche_data() -> None:
    """Szenario 13: SLF Lawinen- und Schneedaten abrufen."""
    params = SimpleQueryInput(limit=5, response_format=ResponseFormat.MARKDOWN)
    result = await wsl_get_avalanche_data(params)
    assert "Lawinen" in result or "SLF" in result or "Datensätze gefunden" in result
    print(f"  ✓ Lawinendaten: {len(result)} Zeichen")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 14: Walddaten (LFI, Sanasilva)
#  Prüft: wsl_get_forest_data Spezial-Tool
# ═══════════════════════════════════════════════════════════════════════════════

async def test_14_forest_data() -> None:
    """Szenario 14: Walddaten inkl. Forstinventar LFI."""
    params = SimpleQueryInput(limit=6, response_format=ResponseFormat.JSON)
    result = await wsl_get_forest_data(params)
    data = json.loads(result)
    assert data["total_found"] > 0, "Keine Walddaten gefunden"
    assert len(data["datasets"]) <= 6
    print(f"  ✓ Walddaten (JSON): {data['total_found']} Treffer")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 15: Naturgefahren-Daten
#  Prüft: wsl_get_naturgefahren_data Spezial-Tool
# ═══════════════════════════════════════════════════════════════════════════════

async def test_15_naturgefahren_data() -> None:
    """Szenario 15: Naturgefahren-Daten (Lawinen, Murgänge, Steinschlag)."""
    params = SimpleQueryInput(limit=8, response_format=ResponseFormat.MARKDOWN)
    result = await wsl_get_naturgefahren_data(params)
    assert "Naturgefahren" in result
    assert "Datensätze gefunden" in result
    print(f"  ✓ Naturgefahren: Ergebnisse erhalten")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 16: Katalog-Statistiken
#  Prüft: wsl_catalog_stats (Gesamtübersicht mit Domänen-Counts)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_16_catalog_stats() -> None:
    """Szenario 16: Katalog-Übersicht mit Domänen-Statistiken."""
    result = await wsl_catalog_stats()
    assert "Katalog-Übersicht" in result
    assert "Datensätze gesamt:" in result
    assert "Wald" in result
    assert "Biodiversität" in result
    assert "EnviDat Portal" in result
    print(f"  ✓ Katalog-Statistiken: {len(result)} Zeichen")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 17: MCP Resource – Organisation
#  Prüft: envidat://organization/{name} Resource
# ═══════════════════════════════════════════════════════════════════════════════

async def test_17_resource_organization() -> None:
    """Szenario 17: MCP-Resource für Organisation liefert JSON."""
    orgs = await ckan_organization_list(all_fields=True)
    org_slug = orgs[0]["name"]

    result = await get_organization_resource(org_slug)
    data = json.loads(result)
    assert "name" in data, "Organisation-Resource fehlt 'name'"
    assert data["name"] == org_slug
    print(f"  ✓ Resource 'organization/{org_slug}': JSON erhalten")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 18: MCP Resource – Domäne
#  Prüft: envidat://domain/{domain} Resource
# ═══════════════════════════════════════════════════════════════════════════════

async def test_18_resource_domain() -> None:
    """Szenario 18: MCP-Resource für Forschungsdomäne."""
    result = await get_domain_resource("naturgefahren")
    data = json.loads(result)
    assert data["domain"] == "naturgefahren"
    assert data["total"] > 0
    assert isinstance(data["datasets"], list)
    assert len(data["datasets"]) > 0
    for ds in data["datasets"]:
        assert "name" in ds and "url" in ds
    print(f"  ✓ Resource 'domain/naturgefahren': {data['total']} Datensätze")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 19: Fehlerbehandlung – ungültiger Dataset-Slug
#  Prüft: Fehlermeldung bei nicht existierendem Datensatz
# ═══════════════════════════════════════════════════════════════════════════════

async def test_19_error_invalid_dataset() -> None:
    """Szenario 19: Fehlerbehandlung bei ungültigem Datensatz-Slug."""
    params = GetDatasetInput(id_or_slug="dieser-datensatz-existiert-sicher-nicht-xyz-999")
    result = await wsl_get_dataset(params)
    # Sollte eine Fehlermeldung zurückgeben, nicht crashen
    assert "Fehler" in result or "error" in result.lower() or "nicht gefunden" in result.lower()
    print(f"  ✓ Fehler bei ungültigem Slug: '{result[:80]}...'")


# ═══════════════════════════════════════════════════════════════════════════════
#  SZENARIO 20: Pydantic-Validierung – BBox-Validierung
#  Prüft: SearchByLocationInput lehnt ungültige Koordinaten ab
# ═══════════════════════════════════════════════════════════════════════════════

async def test_20_pydantic_validation() -> None:
    """Szenario 20: Pydantic-Validierung bei ungültigen Eingaben."""
    errors_caught = 0

    # Test 1: max_lon <= min_lon
    try:
        SearchByLocationInput(min_lon=10.0, min_lat=46.0, max_lon=8.0, max_lat=47.0)
    except Exception:
        errors_caught += 1

    # Test 2: max_lat <= min_lat
    try:
        SearchByLocationInput(min_lon=8.0, min_lat=47.0, max_lon=10.0, max_lat=46.0)
    except Exception:
        errors_caught += 1

    # Test 3: Leerer Suchbegriff bei SearchDatasetsInput
    try:
        SearchDatasetsInput(query="")
    except Exception:
        errors_caught += 1

    # Test 4: Limit ausserhalb des Bereichs
    try:
        SearchDatasetsInput(query="test", limit=100)
    except Exception:
        errors_caught += 1

    assert errors_caught == 4, f"Nur {errors_caught}/4 Validierungsfehler abgefangen"
    print(f"  ✓ Pydantic-Validierung: {errors_caught}/4 ungültige Eingaben korrekt abgelehnt")


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST-RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

async def run_all_tests() -> None:
    tests = [
        ("01 – Volltextsuche JSON-Format",              test_01_search_json_format),
        ("02 – Suche mit Organisations-Filter",         test_02_search_with_org_filter),
        ("03 – Dataset-Details Markdown",               test_03_dataset_details_markdown),
        ("04 – Dataset-Details JSON",                   test_04_dataset_details_json),
        ("05 – Alle 5 Domänen",                        test_05_all_domains),
        ("06 – Domäne schnee_eis JSON",                test_06_domain_json),
        ("07 – Räumliche Suche Davos",                 test_07_spatial_search_davos),
        ("08 – Räumliche Suche + Suchbegriff",         test_08_spatial_search_with_query),
        ("09 – Organisationen auflisten",              test_09_list_organizations),
        ("10 – Organisation-Details mit Datensätzen",  test_10_organization_details),
        ("11 – Tags nach Präfix filtern",              test_11_tags_with_prefix),
        ("12 – Neueste Datensätze",                    test_12_recent_datasets),
        ("13 – Lawinendaten (SLF)",                    test_13_avalanche_data),
        ("14 – Walddaten (LFI) JSON",                 test_14_forest_data),
        ("15 – Naturgefahren-Daten",                   test_15_naturgefahren_data),
        ("16 – Katalog-Statistiken",                   test_16_catalog_stats),
        ("17 – MCP Resource Organisation",             test_17_resource_organization),
        ("18 – MCP Resource Domäne",                   test_18_resource_domain),
        ("19 – Fehlerbehandlung ungültiger Slug",      test_19_error_invalid_dataset),
        ("20 – Pydantic-Validierung",                  test_20_pydantic_validation),
    ]

    print("\n" + "=" * 65)
    print("  WSL/EnviDat MCP Server - 20 Testszenarien")
    print("=" * 65 + "\n")

    passed = failed = 0
    failed_names = []

    for name, test_fn in tests:
        print(f"> {name}")
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ FEHLER: {e}")
            traceback.print_exc()
            failed += 1
            failed_names.append(name)
        print()

    print("=" * 65)
    print(f"  Ergebnis: {passed}/{len(tests)} Tests bestanden")
    if failed:
        print(f"  {failed} Test(s) fehlgeschlagen:")
        for fn in failed_names:
            print(f"    - {fn}")
    else:
        print("  ✅ Alle 20 Szenarien bestanden!")
    print("=" * 65 + "\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
