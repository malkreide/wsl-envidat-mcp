"""Unit-Tests für die 10 MCP-Tools mit gemocktem HTTP-Layer.

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
from mcp.server.fastmcp.exceptions import ToolError

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsl_envidat_mcp.api_client import ENVIDAT_API_BASE  # noqa: E402
from wsl_envidat_mcp.server import (  # noqa: E402
    GetDatasetInput,
    GetOrganizationInput,
    GetRecentDatasetsInput,
    ListTagsInput,
    ResponseFormat,
    SearchInput,
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
    wsl_search,
)


def _ok(payload: Any) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": payload})


# ─── Tool 1: wsl_search (unified) ────────────────────────────────────────────


@respx.mock
async def test_wsl_search_query_markdown(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_search(SearchInput(query="snow avalanche", limit=5))

    assert "«snow avalanche»" in out
    assert "Fatal avalanche accidents" in out
    assert "815 Datensätze gefunden" in out


@respx.mock
async def test_wsl_search_json_includes_ogd_attribution(
    sample_search_response: dict[str, Any],
) -> None:
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    out = await wsl_search(
        SearchInput(query="forest", response_format=ResponseFormat.JSON)
    )
    parsed = json.loads(out)
    assert parsed["total_found"] == 815
    assert len(parsed["datasets"]) == 2
    # CH-004: OGD-Attribution-Felder in jedem JSON-Output
    assert "EnviDat" in parsed["source"]
    assert parsed["provenance"] == "live_api"
    assert parsed["license"]
    assert parsed["retrieved_at"]
    assert parsed["datasets"][0]["license"] == "Creative Commons Attribution"


@respx.mock
async def test_wsl_search_empty_returns_tag_suggestions() -> None:
    """ARCH-003: leeres Resultat liefert verwandte Tags als Hinweis."""
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(
            200,
            json={"success": True, "result": {"count": 0, "results": []}},
        )
    )
    respx.get(f"{ENVIDAT_API_BASE}/tag_list").mock(
        return_value=httpx.Response(
            200,
            json={"success": True, "result": ["xyzzy-test", "xyzzy-data"]},
        )
    )

    out = await wsl_search(SearchInput(query="xyzzy"))
    assert "Keine Datensätze gefunden" in out
    assert "verwandte Tags" in out
    assert "xyzzy-test" in out


@respx.mock
async def test_wsl_search_raises_toolerror_on_timeout() -> None:
    """OBS-001: Fehler werden als ToolError raised."""
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        side_effect=httpx.TimeoutException("timeout")
    )

    with pytest.raises(ToolError, match="Zeitüberschreitung"):
        await wsl_search(SearchInput(query="snow"))


def test_search_input_requires_at_least_one_filter() -> None:
    """ARCH-006: wsl_search verlangt mindestens einen Filter."""
    with pytest.raises(ValueError, match="query/domain/organization/bbox"):
        SearchInput()


@respx.mock
async def test_wsl_search_by_domain(
    sample_search_response: dict[str, Any],
) -> None:
    """Domain-only Suche nutzt den kuratierten Domain-Keyword."""
    route = respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )
    out = await wsl_search(SearchInput(domain=WSLDomain.WALD))
    assert "Domäne" in out
    # Der erste Domain-Keyword für 'wald' ist 'forest' (build_domain_query)
    sent_url = str(route.calls[0].request.url)
    assert "q=forest" in sent_url


@respx.mock
async def test_wsl_search_bbox_passes_ext_bbox_param(
    sample_search_response: dict[str, Any],
) -> None:
    """bbox-Filter wird als ext_bbox-Query-Param weitergereicht."""
    route = respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )
    out = await wsl_search(SearchInput(bbox=[8.35, 47.15, 8.98, 47.72]))
    sent_url = str(route.calls[0].request.url)
    assert "ext_bbox=8.35%2C47.15%2C8.98%2C47.72" in sent_url
    assert "BBox" in out


def test_search_input_validates_bbox_order() -> None:
    """ARCH-006: max_lon > min_lon, max_lat > min_lat enforced."""
    with pytest.raises(ValueError, match="max_lon"):
        SearchInput(bbox=[10.0, 46.0, 5.0, 47.0])
    with pytest.raises(ValueError, match="max_lat"):
        SearchInput(bbox=[5.0, 47.0, 10.0, 46.0])


def test_search_input_rejects_invalid_bbox_size() -> None:
    """bbox muss exakt 4 Werte haben."""
    with pytest.raises(ValueError):
        SearchInput(bbox=[5.0, 46.0, 10.0])


@respx.mock
async def test_wsl_search_combines_query_and_organization(
    sample_search_response: dict[str, Any],
) -> None:
    """query + organization werden als q + fq kombiniert."""
    route = respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )
    await wsl_search(SearchInput(query="bark beetle", organization="wsl"))
    sent_url = str(route.calls[0].request.url)
    assert "q=bark+beetle" in sent_url or "q=bark%20beetle" in sent_url
    assert "fq=organization%3Awsl" in sent_url


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
async def test_wsl_get_dataset_404_raises_toolerror() -> None:
    """OBS-001: 404 wird als ToolError raised."""
    respx.get(f"{ENVIDAT_API_BASE}/package_show").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with pytest.raises(ToolError, match="nicht gefunden|404"):
        await wsl_get_dataset(GetDatasetInput(id_or_slug="missing-slug"))


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
async def test_wsl_search_all_domains_smoke(
    domain: WSLDomain, sample_search_response: dict[str, Any]
) -> None:
    """Smoke-Test: alle fünf Domain-Werte sind akzeptiert."""
    respx.get(f"{ENVIDAT_API_BASE}/package_search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )
    out = await wsl_search(SearchInput(domain=domain))
    assert "Domäne" in out


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
        SearchInput(query="snow", malicious_field="boom")  # type: ignore[call-arg]


def test_search_input_enforces_limit_bounds() -> None:
    with pytest.raises(ValueError):
        SearchInput(query="ok", limit=999)
