"""Zugriff auf die aufgezeichneten Fixtures unter ``tests/fixtures/``.

Herkunft, Datum, Auswahlregel und SHA-256 stehen je Datei in
``tests/fixtures/PROVENANCE.md``, geschrieben von ``scripts/record_fixtures.py``.

Ein fehlender Name ist ein Fehler und keine leere Struktur: Der Rueckfallwert
eines Lookups waere sonst die ganze Ursache — ein Test gegen eine leere Fixture
prueft nichts und meldet Erfolg.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_json(name: str) -> Any:
    """Die aufgezeichnete Antwort zu ``name``, als frische Kopie.

    Die Kopie ist Absicht: Die pytest-Fixtures unten geben das Ergebnis an
    Tests weiter, die es veraendern duerfen. Ohne `deepcopy` traegt ein Test
    seine Aenderung in den naechsten — und dann haengt das Ergebnis an der
    Reihenfolge statt am Pruefgegenstand.
    """
    path = FIXTURES / f"{name}.json"
    if not path.is_file():
        available = sorted(p.stem for p in FIXTURES.glob("*.json"))
        raise FileNotFoundError(
            f"Keine Fixture {name!r} unter {FIXTURES}. Vorhanden: {available}. "
            "Neu aufzeichnen mit `python scripts/record_fixtures.py`."
        )
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))
