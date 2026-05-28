"""Unit-Tests für die 12 MCP-Tools mit gemocktem HTTP-Layer.

Alle Tests in dieser Datei laufen offline — keine Live-Calls zu envidat.ch.
Default-CI führt diese Suite via `pytest -m "not live"` aus.

Pro Tool werden gemockte Erfolgs- und (wo sinnvoll) Fehlerfälle abgedeckt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsl_envidat_mcp.api_client import ENVIDAT_API_BASE  # noqa: E402
from wsl_envidat_mcp.server import (  # noqa: E402
    GetDatasetInput,
    GetOrganizationInput,
    GetRecentDatasetsInput,
    ListTagsInput,
    ResponseFormat,
    SearchByDomainInput,
    SearchByLocationInput,
    SearchDatasetsInput,
    SimpleQueryInput,
    WSLDomain,
    get_domain_resource,
    get_organization_resource,
    wsl_catalog_stats,
    wsl_get_avalanche_data,
    wsl_get_dataset,
    wsl_get_forest_data,
    wsl_get_naturgefahren_data,
    wsl_get_organization,
    wsl_get_recent_datasets,
    wsl_list_organizations,
    wsl_list_tags,
    wsl_search_by_domain,
    wsl_search_by_location,
    wsl_search_datasets,
)


def _ok(payload: Any) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": payload})


# ─── Tool 1: wsl_search_datasets ─────────────────────────────────────────────


@respx.mock
async def test_wsl_search_datasets_markdown(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_search_datasets(
        SearchDatasetsInput(query="snow avalanche", limit=5)
    )

    assert "Suchergebnisse für «snow avalanche»" in out
    assert "Fatal avalanche accidents" in out
    assert "815 Datensätze gefunden" in out


@respx.mock
async def test_wsl_search_datasets_json(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_search_datasets(
        SearchDatasetsInput(query="forest", response_format=ResponseFormat.JSON)
    )
    parsed = json.loads(out)
    assert parsed["total_found"] == 815
    assert len(parsed["datasets"]) == 2


@respx.mock
async def test_wsl_search_datasets_empty() -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(
            200,
            json={"success": True, "result": {"count": 0, "results": []}},
        )
    )

    out = await wsl_search_datasets(SearchDatasetsInput(query="xyzzy"))
    assert "Keine Datensätze gefunden" in out


@respx.mock
async def test_wsl_search_datasets_handles_timeout() -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        side_effect=httpx.TimeoutException("timeout")
    )

    out = await wsl_search_datasets(SearchDatasetsInput(query="snow"))
    assert "Zeitüberschreitung" in out


# ─── Tool 2: wsl_get_dataset ─────────────────────────────────────────────────


@respx.mock
async def test_wsl_get_dataset_markdown(sample_dataset: dict[str, Any]) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_show").mock(
        return_value=_ok(sample_dataset)
    )

    out = await wsl_get_dataset(GetDatasetInput(id_or_slug=sample_dataset["name"]))
    assert "Fatal avalanche accidents" in out
    assert sample_dataset["name"] in out
    assert "Creative Commons Attribution" in out
    assert "## Ressourcen" in out


@respx.mock
async def test_wsl_get_dataset_404() -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_show").mock(
        return_value=httpx.Response(404, text="not found")
    )

    out = await wsl_get_dataset(GetDatasetInput(id_or_slug="missing-slug"))
    assert "404" in out or "nicht gefunden" in out


# ─── Tool 3: wsl_search_by_domain ────────────────────────────────────────────


@respx.mock
async def test_wsl_search_by_domain_wald(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_search_by_domain(SearchByDomainInput(domain=WSLDomain.WALD))
    assert "Forschungsdomäne" in out
    assert "Wald" in out


@pytest.mark.parametrize(
    "domain",
    [
        WSLDomain.WALD,
        WSLDomain.BIODIVERSITAET,
        WSLDomain.NATURGEFAHREN,
        WSLDomain.SCHNEE_EIS,
        WSLDomain.LANDSCHAFT,
    ],
)
@respx.mock
async def test_wsl_search_by_domain_all_domains(
    domain: WSLDomain, sample_search_response: dict[str, Any]
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )
    out = await wsl_search_by_domain(SearchByDomainInput(domain=domain))
    assert "Forschungsdomäne" in out


# ─── Tool 4: wsl_search_by_location ──────────────────────────────────────────


@respx.mock
async def test_wsl_search_by_location_bbox_zh(
    sample_search_response: dict[str, Any],
) -> None:
    route = respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_search_by_location(
        SearchByLocationInput(
            min_lon=8.35, min_lat=47.15, max_lon=8.98, max_lat=47.72
        )
    )
    assert "BBox" in out
    # ext_bbox-Parameter muss als Query-String mitgegeben werden
    sent_url = str(route.calls[0].request.url)
    assert "ext_bbox=8.35%2C47.15%2C8.98%2C47.72" in sent_url


def test_wsl_search_by_location_validates_bbox() -> None:
    with pytest.raises(ValueError, match="max_lon"):
        SearchByLocationInput(min_lon=10.0, min_lat=46.0, max_lon=5.0, max_lat=47.0)


# ─── Tool 5: wsl_list_organizations ──────────────────────────────────────────


@respx.mock
async def test_wsl_list_organizations(
    sample_orgs_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/organization_list").mock(
        return_value=httpx.Response(200, json=sample_orgs_response)
    )

    out = await wsl_list_organizations()
    assert "WSL-Forschungseinheiten" in out
    assert "WSL-Institut SLF" in out
    assert "`slf`" in out


# ─── Tool 6: wsl_get_organization ────────────────────────────────────────────


@respx.mock
async def test_wsl_get_organization(
    sample_org_show_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/organization_show").mock(
        return_value=httpx.Response(200, json=sample_org_show_response)
    )

    out = await wsl_get_organization(GetOrganizationInput(name="slf"))
    assert "WSL-Institut SLF" in out
    assert "Datensätze" in out


# ─── Tool 7: wsl_list_tags ───────────────────────────────────────────────────


@respx.mock
async def test_wsl_list_tags_with_query(
    sample_tag_list_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/tag_list").mock(
        return_value=httpx.Response(200, json=sample_tag_list_response)
    )

    out = await wsl_list_tags(ListTagsInput(query="snow", limit=10))
    assert "«snow»" in out
    assert "snow" in out
    assert "snowpack" in out


# ─── Tool 8: wsl_get_recent_datasets ─────────────────────────────────────────


@respx.mock
async def test_wsl_get_recent_datasets(
    sample_search_response: dict[str, Any],
) -> None:
    route = respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_get_recent_datasets(GetRecentDatasetsInput(limit=5))
    assert "aktualisierte WSL-Datensätze" in out
    # Sort-Param muss "metadata_modified desc" sein
    sent_url = str(route.calls[0].request.url)
    assert "metadata_modified+desc" in sent_url or "metadata_modified%20desc" in sent_url


# ─── Tool 9: wsl_get_avalanche_data ──────────────────────────────────────────


@respx.mock
async def test_wsl_get_avalanche_data(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_get_avalanche_data(SimpleQueryInput(limit=5))
    assert "Lawinen" in out or "SLF" in out


@respx.mock
async def test_wsl_get_avalanche_data_fallback() -> None:
    """Wenn der org=slf-Filter null Treffer liefert, läuft der Fallback ohne Filter."""
    empty = {"success": True, "result": {"count": 0, "results": []}}
    non_empty_sample = {
        "success": True,
        "result": {
            "count": 1,
            "results": [
                {
                    "name": "fallback-dataset",
                    "title": "Fallback Avalanche Dataset",
                    "notes": "fallback",
                    "metadata_modified": "2024-01-01",
                    "organization": {"name": "wsl"},
                    "tags": [],
                    "resources": [],
                }
            ],
        },
    }
    route = respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=non_empty_sample)]
    )

    out = await wsl_get_avalanche_data(SimpleQueryInput(limit=5))
    assert route.call_count == 2
    assert "Fallback Avalanche" in out


# ─── Tool 10: wsl_get_forest_data ────────────────────────────────────────────


@respx.mock
async def test_wsl_get_forest_data(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_get_forest_data(SimpleQueryInput(limit=5))
    assert "Wald" in out or "LFI" in out


# ─── Tool 11: wsl_get_naturgefahren_data ─────────────────────────────────────


@respx.mock
async def test_wsl_get_naturgefahren_data(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_get_naturgefahren_data(SimpleQueryInput(limit=5))
    assert "Naturgefahren" in out


# ─── Tool 12: wsl_catalog_stats ──────────────────────────────────────────────


@respx.mock
async def test_wsl_catalog_stats(
    sample_search_response: dict[str, Any],
    sample_orgs_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )
    respx.get(f"{ENVIDAT_API_BASE}/organization_list").mock(
        return_value=httpx.Response(200, json=sample_orgs_response)
    )

    out = await wsl_catalog_stats()
    assert "Katalog-Übersicht" in out
    assert "Forschungseinheiten:" in out
    # Top-Organisations-Sektion
    assert "WSL-Institut SLF" in out or "WSL" in out


# ─── Resources ───────────────────────────────────────────────────────────────


@respx.mock
async def test_resource_organization(
    sample_org_show_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/organization_show").mock(
        return_value=httpx.Response(200, json=sample_org_show_response)
    )

    out = await get_organization_resource("slf")
    parsed = json.loads(out)
    assert parsed["name"] == "slf"


@respx.mock
async def test_resource_domain(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await get_domain_resource("wald")
    parsed = json.loads(out)
    assert parsed["domain"] == "wald"
    assert parsed["total"] == 815
    assert len(parsed["datasets"]) == 2


# ─── Pydantic-Validation der Tool-Inputs ─────────────────────────────────────


def test_search_input_rejects_extra_fields() -> None:
    with pytest.raises(ValueError, match="forbidden|Extra inputs"):
        SearchDatasetsInput(query="snow", malicious_field="boom")  # type: ignore[call-arg]


def test_search_input_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        SearchDatasetsInput(query="")


def test_search_input_enforces_limit_bounds() -> None:
    with pytest.raises(ValueError):
        SearchDatasetsInput(query="ok", limit=999)
