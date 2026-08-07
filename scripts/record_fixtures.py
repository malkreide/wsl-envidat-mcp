#!/usr/bin/env python3
"""Zeichnet die Unit-Test-Fixtures von der echten EnviDat-CKAN-Instanz auf.

    python scripts/record_fixtures.py

WARUM ES DIESES SKRIPT GIBT. Ein handgeschriebener Mock kodiert die Annahme
seines Autors und kann sie deshalb prinzipiell nicht widerlegen: Produktivcode
und Fixture stammen aus demselben Kopf, derselben Stunde, derselben Lektuere der
Doku. Wo beide irren, irren beide gleich, und die Suite bleibt gruen.

Ohne Aufzeichnungsdatum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht»
nicht mehr zu unterscheiden — die Datei sieht gleich aus.

**Es sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel je Datei steht in
`tests/fixtures/PROVENANCE.md`. Wo gekuerzt wird, bleiben `count` und
`package_count` auf dem echten Wert: Eine Fixture, die stillschweigend
behauptet, der Bestand sei kleiner, waere genau der Fehler, gegen den das hier
angeht.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ENVIDAT = "https://www.envidat.ch/api/action"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Derselbe Datensatz, den die handgeschriebene Fixture nannte — er existiert
# wirklich, nur trug die Fixture 9 seiner 42 Felder und erfundene `extras`.
DATASET = "fatal-avalanche-accidents-in-switzerland-since-1936-37"
SEARCH_ROWS = 2
# Eine ECHTE Organisation. Die handgeschriebene Fixture nannte «slf» und
# «wsl» — beide gibt es in EnviDat nicht; `organization_show?id=slf` antwortet
# mit 404. Folgenlos, weil der Produktivcode keine Organisationsnamen fest
# verdrahtet (die Domaenen laufen ueber Stichwoerter), aber erfunden war es
# trotzdem.
ORG = "avalanche-formation"
TAG_QUERY = "snow"
TAG_LIMIT = 8


def record() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict] = []

    def write(name: str, payload: Any, url: str, rule: str) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        print(f"ok  {name:<28} {len(text.encode('utf-8')):>7} B")

    def call(action: str, **params: Any) -> Any:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{ENVIDAT}/{action}" + (f"?{query}" if query else "")
        r = client.get(url)
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            raise SystemExit(f"{action}: CKAN meldet success=false")
        return body["result"], url

    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        # 1) Volltextsuche mit explizitem `rows`. CKAN liefert ohne den
        #    Parameter eine willkuerliche Teilmenge — hier geht er raus, und
        #    `count` bleibt der echte Gesamtbestand.
        result, url = call("package_search", rows=SEARCH_ROWS)
        if len(result.get("results", [])) > SEARCH_ROWS:
            raise SystemExit(f"package_search: mehr als {SEARCH_ROWS} Treffer trotz rows")
        write(
            "package_search.json",
            {"success": True, "result": result},
            url,
            f"{len(result['results'])} Datensaetze; `count` ist der echte "
            f"Gesamtbestand ({result.get('count')})",
        )

        # 2) Ein vollstaendiger Datensatz.
        result, url = call("package_show", id=DATASET)
        tags = [t.get("name", "") for t in result.get("tags", [])]
        if not tags:
            raise SystemExit(f"package_show {DATASET}: keine Tags — Antwortform geaendert?")
        write(
            "package_show.json",
            {"success": True, "result": result},
            url,
            f"vollstaendig, {len(result)} Felder (die handgeschriebene "
            f"Vorgaengerin hatte 9); {len(tags)} Tags, so geschrieben wie die "
            "Quelle sie fuehrt",
        )

        # 3) Organisationen.
        result, url = call("organization_list", all_fields="true")
        if not isinstance(result, list) or not result:
            raise SystemExit("organization_list: leer oder falsche Form")
        write(
            "organization_list.json",
            {"success": True, "result": result},
            url,
            f"vollstaendig, {len(result)} Organisationen",
        )

        result, url = call("organization_show", id=ORG, include_datasets="true")
        packages = result.get("packages") or []
        # Auf zwei Pakete kuerzen; `package_count` bleibt der echte Wert.
        result["packages"] = packages[:2]
        write(
            "organization_show.json",
            {"success": True, "result": result},
            url,
            f"Organisation «{ORG}»; `packages` auf die ersten 2 von "
            f"{len(packages)} gekuerzt, `package_count` unveraendert "
            f"({result.get('package_count')})",
        )

        # 4) Tags. Die Schreibweise ist hier der Punkt: EnviDat fuehrt sie in
        #    GROSSBUCHSTABEN, die handgeschriebene Fixture hatte
        #    Kleinschreibung. Die Suche selbst ist upstream case-insensitiv
        #    (geprueft mit avalanche/AVALANCHE/Avalanche: je 37 Treffer), die
        #    ausgelieferten Werte sind es nicht.
        result, url = call("tag_list", query=TAG_QUERY)
        if not result:
            raise SystemExit(f"tag_list?query={TAG_QUERY}: keine Treffer")
        kept = list(result)[:TAG_LIMIT]
        write(
            "tag_list.json",
            {"success": True, "result": kept},
            url,
            f"die ersten {len(kept)} von {len(result)} Tags zu «{TAG_QUERY}», "
            "in der Schreibweise der Quelle",
        )

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von `{ENVIDAT}`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "**Es sind Ausschnitte, keine Vollabzuege.** Wo gekuerzt wurde, bleiben",
        "die Zaehlfelder (`count`, `package_count`) auf dem echten Wert.",
        "",
        "**Tags stehen in der Schreibweise der Quelle** — EnviDat fuehrt sie in",
        "GROSSBUCHSTABEN. Sie kleinzuschreiben wuerde eine Eigenschaft",
        "wegputzen, die im Repo sichtbar bleiben soll; die Tag-*Suche* ist",
        "upstream case-insensitiv, die ausgelieferten *Werte* sind es nicht.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except httpx.HTTPError as exc:
        print(f"FEHLER: Quelle nicht erreichbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
