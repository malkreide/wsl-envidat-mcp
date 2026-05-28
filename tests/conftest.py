"""Gemeinsame pytest-Fixtures für die Unit-Test-Suite.

Stellt Sample-CKAN-Antworten und einen respx-Helper bereit, damit
Unit-Tests offline laufen können (keine Live-Calls zu envidat.ch).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# src/ ins sys.path aufnehmen für ungebundene Imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_dataset() -> dict[str, Any]:
    """Ein realistisch geformter CKAN-Package-Eintrag."""
    return {
        "name": "fatal-avalanche-accidents-in-switzerland-since-1936-37",
        "title": "Fatal avalanche accidents in Switzerland since 1936/37",
        "notes": (
            "This dataset contains records of fatal avalanche accidents "
            "in Switzerland reaching back to the winter season 1936/37."
        ),
        "metadata_modified": "2024-09-15T08:30:00",
        "metadata_created": "2017-03-10T11:00:00",
        "organization": {"name": "slf", "title": "WSL-Institut SLF"},
        "tags": [
            {"name": "avalanche"},
            {"name": "snow"},
            {"name": "accidents"},
            {"name": "switzerland"},
        ],
        "resources": [
            {
                "id": "res-1",
                "name": "Avalanche accidents CSV",
                "format": "CSV",
                "url": "https://www.envidat.ch/dataset/foo/resource/res-1",
                "size": 102400,
            },
        ],
        "license_title": "Creative Commons Attribution",
        "extras": [
            {"key": "authors", "value": "Frank Techel, SLF"},
            {"key": "publication_year", "value": "2024"},
        ],
    }


@pytest.fixture
def sample_search_response(sample_dataset: dict[str, Any]) -> dict[str, Any]:
    """Eine CKAN package_search-Antwort mit zwei Datensätzen."""
    second = dict(sample_dataset)
    second["name"] = "swiss-national-forest-inventory-lfi"
    second["title"] = "Swiss National Forest Inventory (LFI)"
    second["organization"] = {"name": "wsl", "title": "WSL"}
    return {
        "success": True,
        "result": {
            "count": 815,
            "results": [sample_dataset, second],
        },
    }


@pytest.fixture
def sample_orgs_response() -> dict[str, Any]:
    """Eine CKAN organization_list-Antwort mit zwei Organisationen."""
    return {
        "success": True,
        "result": [
            {
                "name": "wsl",
                "title": "WSL",
                "description": "Eidg. Forschungsanstalt für Wald, Schnee und Landschaft",
                "package_count": 500,
            },
            {
                "name": "slf",
                "title": "WSL-Institut SLF",
                "description": "Schnee- und Lawinenforschung",
                "package_count": 120,
            },
        ],
    }


@pytest.fixture
def sample_org_show_response(sample_dataset: dict[str, Any]) -> dict[str, Any]:
    """Eine CKAN organization_show-Antwort mit Paket-Liste."""
    return {
        "success": True,
        "result": {
            "name": "slf",
            "title": "WSL-Institut SLF",
            "description": "Schnee- und Lawinenforschung",
            "package_count": 120,
            "packages": [sample_dataset],
        },
    }


@pytest.fixture
def sample_tag_list_response() -> dict[str, Any]:
    """Eine CKAN tag_list-Antwort."""
    return {
        "success": True,
        "result": ["snow", "snowpack", "snow-depth", "snowmelt"],
    }
