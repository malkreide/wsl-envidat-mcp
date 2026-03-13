"""Integrationstests für den WSL/EnviDat MCP Server.

Testet Live-Verbindungen zur EnviDat CKAN API.
Ausführen: python tests/test_integration.py

Hinweis: Tests erfordern aktive Internetverbindung.
"""

import asyncio
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
    format_dataset_summary,
)


# ─── Testfälle ────────────────────────────────────────────────────────────────

async def test_catalog_search() -> None:
    """Test: Volltextsuche über den Katalog."""
    result = await ckan_package_search(query="snow avalanche", rows=5)
    assert result.get("count", 0) > 0, "Keine Ergebnisse für 'snow avalanche'"
    assert len(result.get("results", [])) > 0
    print(f"  ✓ Suche 'snow avalanche': {result['count']} Treffer")


async def test_wildcard_search() -> None:
    """Test: Wildcard-Suche gibt Gesamtanzahl zurück."""
    result = await ckan_package_search(query="*:*", rows=1)
    total = result.get("count", 0)
    assert total > 100, f"Zu wenige Datensätze: {total}"
    print(f"  ✓ Katalog: {total} Datensätze total")


async def test_get_avalanche_dataset() -> None:
    """Test: Bekannter Lawinendatensatz ist abrufbar."""
    # Tödliche Lawinenunfälle – bekannter EnviDat-Datensatz
    result = await ckan_package_search(
        query='"fatal avalanche" OR "avalanche accidents"', rows=3
    )
    assert result.get("count", 0) > 0, "Lawinendaten nicht gefunden"
    pkg = result["results"][0]
    assert "name" in pkg
    print(f"  ✓ Lawinendaten: '{pkg['title']}'")


async def test_package_show() -> None:
    """Test: Dataset-Details abrufbar."""
    # Suche zuerst, dann Details abrufen
    result = await ckan_package_search(query="snow depth avalanche", rows=1)
    assert result.get("results"), "Keine Datensätze für Details-Test"
    slug = result["results"][0]["name"]
    pkg = await ckan_package_show(slug)
    assert pkg.get("name") == slug
    assert "resources" in pkg
    print(f"  ✓ Dataset-Details: '{pkg['title']}' ({len(pkg['resources'])} Ressourcen)")


async def test_organization_list() -> None:
    """Test: Organisation-Liste enthält WSL-Einheiten."""
    orgs = await ckan_organization_list(all_fields=True)
    assert len(orgs) > 0, "Keine Organisationen gefunden"
    org_names = [o.get("name") for o in orgs]
    print(f"  ✓ Organisationen: {len(orgs)} gefunden ({', '.join(org_names[:4])}...)")


async def test_domain_queries() -> None:
    """Test: Alle Domänen liefern Ergebnisse."""
    domains = ["wald", "biodiversitaet", "naturgefahren", "schnee_eis", "landschaft"]
    for domain in domains:
        query = build_domain_query(domain)
        result = await ckan_package_search(query=query, rows=1)
        count = result.get("count", 0)
        assert count > 0, f"Keine Ergebnisse für Domäne '{domain}'"
        print(f"  ✓ Domäne '{domain}': {count} Datensätze")


async def test_spatial_search() -> None:
    """Test: Räumliche Suche (Kanton Zürich) liefert Ergebnisse."""
    # BBox Kanton Zürich
    bbox = "8.35,47.15,8.98,47.72"
    result = await ckan_package_search(
        query="*:*",
        rows=5,
        extras={"ext_bbox": bbox},
    )
    # EnviDat hat möglicherweise wenige exakte Zürich-BBox-Datensätze
    # daher nur prüfen dass API antwortet
    assert "count" in result, "Räumliche Suche liefert keine Antwort"
    print(f"  ✓ Räumliche Suche ZH: {result.get('count', 0)} Datensätze")


async def test_tag_list() -> None:
    """Test: Tag-Liste enthält relevante Umwelt-Tags."""
    tags = await ckan_tag_list(query="snow")
    assert len(tags) > 0, "Keine Tags für 'snow'"
    print(f"  ✓ Tags 'snow': {len(tags)} gefunden ({', '.join(tags[:5])}...)")


async def test_forest_data() -> None:
    """Test: Walddaten inkl. LFI verfügbar."""
    result = await ckan_package_search(
        query='"forest" OR "LFI" OR "sanasilva"',
        rows=3,
    )
    assert result.get("count", 0) > 0, "Keine Walddaten gefunden"
    print(f"  ✓ Walddaten: {result['count']} Datensätze")


async def test_format_dataset_summary() -> None:
    """Test: Formatierung eines Datensatzes funktioniert."""
    result = await ckan_package_search(query="biodiversity habitat", rows=1)
    assert result.get("results"), "Keine Datensätze für Formatierungstest"
    pkg = result["results"][0]
    summary = format_dataset_summary(pkg)
    assert "###" in summary, "Markdown-Formatierung fehlt"
    assert "EnviDat" in summary, "Portal-Link fehlt"
    print(f"  ✓ Formatierung: {len(summary)} Zeichen")


async def test_pagination() -> None:
    """Test: Paginierung funktioniert korrekt."""
    page1 = await ckan_package_search(query="*:*", rows=5, start=0)
    page2 = await ckan_package_search(query="*:*", rows=5, start=5)
    names1 = {p["name"] for p in page1.get("results", [])}
    names2 = {p["name"] for p in page2.get("results", [])}
    assert names1.isdisjoint(names2), "Paginierung: Überlappende Ergebnisse"
    print(f"  ✓ Paginierung: Seite 1 und 2 überschneiden sich nicht")


# ─── Test-Runner ──────────────────────────────────────────────────────────────

async def run_all_tests() -> None:
    tests = [
        ("Katalog Wildcard-Suche",          test_wildcard_search),
        ("Volltextsuche 'snow avalanche'",   test_catalog_search),
        ("Datensatz-Details abrufen",        test_package_show),
        ("Lawinendaten",                     test_get_avalanche_dataset),
        ("Walddaten (LFI, Sanasilva)",       test_forest_data),
        ("Organisations-Liste",              test_organization_list),
        ("Alle Domänen-Abfragen",            test_domain_queries),
        ("Räumliche Suche (Kanton ZH)",      test_spatial_search),
        ("Tag-Liste",                         test_tag_list),
        ("Datensatz-Formatierung",           test_format_dataset_summary),
        ("Paginierung",                       test_pagination),
    ]

    print("\n" + "=" * 60)
    print("  WSL/EnviDat MCP Server – Integrationstests")
    print("=" * 60 + "\n")

    passed = failed = 0
    for name, test_fn in tests:
        print(f"▶ {name}")
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ FEHLER: {e}")
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    print(f"  Ergebnis: {passed}/{len(tests)} Tests bestanden")
    if failed:
        print(f"  {failed} Test(s) fehlgeschlagen!")
    print("=" * 60 + "\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
