# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Hinzugefuegt

- **Frischehinweise auf den auflistenden Methoden** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides auf
  «sofort veraltet, nie geteilt» — wer nichts übergibt, lässt jeden Client bei
  jeder Verbindung neu auflisten. `resources/read` und `prompts/get` bleiben
  ohne Hinweis: das wäre eine Zusicherung über den Inhalt statt über das
  Verzeichnis.

### Fixed

- **Der Fix vom 2026-08-07 bestätigte `result` und hörte dort auf.** Die Ebene
  darunter blieb offen: Die Formatierer lasen weiter
  `result.get("results", [])`, und eine Strukturänderung eine Ebene tiefer
  ergab weiterhin «0 Datensätze gefunden» — dieselbe Antwort wie eine korrekte
  Suche ohne Treffer.

  Dass ein Fix seine eigene Ebene bestätigt und die nächste offen lässt, ist
  die häufigste Form dieses Fehlers: Er **wandert nach unten**, statt zu
  verschwinden.

  Beide Lesestellen laufen jetzt über `ckan_results()`, das `results` **und**
  `count` bestätigt. CKAN liefert beide bei `package_search` immer, auch bei
  null Treffern; `count: 0` mit vorhandenem `results` bleibt eine leere Suche.

  Nachtrag zum Portfolio-Durchlauf
  ([`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md)).

### Hinzugefuegt — die Fixtures sind aufgezeichnet, nicht mehr ausgedacht

**`scripts/record_fixtures.py`** zeichnet fuenf CKAN-Antworten von
`www.envidat.ch` auf und schreibt `tests/fixtures/*` samt `PROVENANCE.md` mit
Quelle, **Aufzeichnungsdatum**, Auswahlregel und SHA-256 je Datei. Ohne Datum
ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht mehr zu
unterscheiden.

**Was der Wechsel aufgedeckt hat — drei Befunde an den Fixtures:**

1. **Die Organisationen `wsl` und `slf` gibt es nicht.**
   `organization_show?id=slf` antwortet mit **HTTP 404**. EnviDat fuehrt 25
   Organisationen mit Slugs wie `avalanche-formation` oder
   `alpine-mass-movements`. Folgenlos, weil der Produktivcode keine
   Organisationsnamen fest verdrahtet — die Domaenen laufen ueber Stichwoerter
   —, aber erfunden war es trotzdem.

2. **Tags stehen in GROSSBUCHSTABEN.** Die Fixture hatte `snow`, `snowpack`;
   die Quelle liefert `SNOW COVER`, `SNOW DEPTH DISTRIBUTION`. Nachgeprueft und
   ausdruecklich **kein** Recall-Problem: Die Tag-*Suche* ist upstream
   case-insensitiv (`avalanche`, `AVALANCHE`, `Avalanche` liefern je 37
   Treffer) — nur die ausgelieferten *Werte* sind es nicht.

3. **Ein Datensatz hat 42 Felder, die Fixture hatte 9** — und ihre `extras`
   (`authors`, `publication_year`) gibt es in der Quelle nicht; dort steht nur
   `deprecatedResources`. Auch das folgenlos: Der Code liest die Package-
   `extras` gar nicht, `extras` ist bei ihm ein Request-Parameter.

Die Gesamtzahl der Datensaetze stand als `815` in der Fixture; gemessen sind es
**858**. Solche Zahlen werden jetzt durchgehend **aus der Fixture abgeleitet**
statt hingeschrieben.

**Kein Befund am Produktivcode.** Wie in `zurich-opendata-mcp`,
`swiss-statistics-mcp` und `meteoswiss-mcp` hat das Aufzeichnen hier nichts
Kaputtes freigelegt.

**Zur Gegenprobe, ausdruecklich:** Abgeleitete Erwartungen lassen sich **nicht**
durch Verbiegen der Fixture pruefen — sie wandern mit. Gegengeprueft wurde
deshalb am Code: Gibt der Server die *gezeigte* statt der *gefundenen* Zahl aus
(genau der Fehler, den Regel 1 beschreibt — eine Teilmenge als Gesamtmenge),
faellt `test_wsl_search_query_markdown`.

Der Rahmen dazu steht im Skill [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill)
unter Regel 5 und im Katalog-Check `OPS-009`.


### Fixed

- **Eine Strukturänderung von EnviDat wurde zu einem leeren Ergebnis.**
  `_parse_response` holte den CKAN-Block mit `data.get("result", {})`. Fällt
  `result` weg oder wandert es — weil die Quelle ihre Antwort umbaut oder die
  Aktion nie richtig war —, dann gelang der Tool-Call, die Antwort war leer, und
  für das Modell war das nicht von «EnviDat kennt diesen Datensatz nicht» zu
  unterscheiden. Ein Ausfall, der wie eine Antwort aussieht.

  `result` wird jetzt bestätigt statt gedefaultet und wirft sonst einen eigenen
  Typ, `UpstreamSchemaError`. Die Meldung nennt die **tatsächlich vorhandenen**
  Schlüssel — die Antwort enthält sie, sie zu verschweigen wäre eine
  Entscheidung gegen die Diagnose — und sagt ausdrücklich, dass dies keine
  Leermenge ist. Der Typ erbt von `ValueError`, damit `handle_api_error` ihn
  weiterhin als API-Fehler formatiert statt als «Unerwarteter Fehler».

  Ein echter CKAN-Fehler (`success: false`) bleibt ein `ValueError` und wird
  **nicht** zum Strukturfehler: Dort hat die Quelle geantwortet und Nein gesagt,
  hier hat sie sich geändert, und die Behebung ist eine andere.

  Gefunden im Portfolio-Durchlauf zu
  [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md)
  am 2026-08-07. Acht Server im Portfolio sprechen mit CKAN, alle acht prüfen
  das `success`-Envelope — und sieben holten `result` danach mit einem stillen
  Default.

- **Der Rückgabetyp von `_parse_response` war falsch, und der Default doppelt.**
  Annotiert war `dict[str, Any]`; `organization_list` und `tag_list` liefern
  eine Liste. Für diese beiden Aktionen war der Ersatzwert `{}` nicht einmal vom
  richtigen Typ — dieselbe Zeile erzeugte also zwei Fehler. Jetzt `Any`, mit der
  Begründung im Docstring.

## [0.2.5] - 2026-08-02

### Fixed

- **`structlog` carried no upper bound, and the index already serves a major past
  the floor.** The declared range was `structlog>=24.1.0`; PyPI has been serving
  `26.1.0`. The artefact does not change — the resolver's answer to the next
  fresh install does, and that is exactly how `swiss-energy-mcp` 0.3.3 became
  uninstallable when `mcp` 2.0.0 removed the module it imported.

  Now `structlog>=24.1.0,<27`. The bound is measured rather than guessed: this package
  installs and imports against `structlog 26.1.0` today, so the cap admits what
  demonstrably works and stops only the next, unknown major.

A dependency range only reaches users through a new release, hence the
version bump. No code changed.

## [0.2.4] - 2026-07-30

### Fixed

- **The User-Agent reports the actual package version again.** The published
  `0.2.3` sent `wsl-envidat-mcp/0.2.0` to every upstream — the version string was
  hardcoded and had been left behind by earlier bumps. The version now comes
  from the package metadata, so it can no longer drift from the package.

## [0.2.0] - 2026-05-28

### Breaking changes

- **Tool consolidation (ARCH-006):** Replaced the three separate search
  tools `wsl_search_datasets`, `wsl_search_by_domain` and
  `wsl_search_by_location` with a single unified `wsl_search` tool that
  accepts optional `query`, `domain`, `organization` and `bbox` filters
  (at least one is required). Total tool surface drops from 12 to 10.

  **Migration**:

  ```python
  # Before (0.1.0)
  wsl_search_datasets(query="snow avalanche", limit=5)
  wsl_search_by_domain(domain="wald")
  wsl_search_by_location(min_lon=8.35, min_lat=47.15,
                         max_lon=8.98, max_lat=47.72)

  # After (0.2.0)
  wsl_search(query="snow avalanche", limit=5)
  wsl_search(domain="wald")
  wsl_search(bbox=[8.35, 47.15, 8.98, 47.72])

  # New: combine filters
  wsl_search(query="bark beetle", organization="wsl",
             bbox=[8.35, 47.15, 8.98, 47.72])
  ```

  The corresponding Pydantic input classes
  (`SearchDatasetsInput` / `SearchByDomainInput` / `SearchByLocationInput`)
  are replaced by a single `SearchInput`.

### Added (Audit-Run 2026-05-27, mcp-audit-skill v1.0.0)

- **Container image** at `ghcr.io/malkreide/wsl-envidat-mcp` (multi-arch,
  non-root uid 1000, distroless-style multi-stage build) — SEC-007
- **`wsl_search` unified search tool** with optional query/domain/
  organization/bbox filters — ARCH-006
- **Empty-result tag suggestions** via tag-prefix heuristic — ARCH-003
- **Structured `<use_case>` / `<important_notes>` / `<example>` tags** in
  tool descriptions (4 search-oriented tools) — ARCH-002
- **`MCP_HOST` env var** (default `127.0.0.1`) for streamable-http
  binding — SEC-016
- **Egress allow-list** (`ALLOWED_HOSTS = {www.envidat.ch, envidat.ch}`)
  with `assert_host_allowed()` and `follow_redirects=False` — SEC-021,
  SEC-005
- **structlog** as runtime dependency, JSON logs on stderr — OBS-003
- **`SUPPORTED_MCP_PROTOCOL_VERSION`** constant with startup-time drift
  warning against `mcp.types.LATEST_PROTOCOL_VERSION` — ARCH-012
- **OGD-CH attribution fields** (`source` / `license` / `provenance` /
  `retrieved_at`) in every JSON search response — CH-004
- **Phase section** in both READMEs declaring Phase 1 (Read-only Wrapper)
  with audit-run status — OPS-002, OPS-003
- **Offline unit-test suite** with respx-mocked tests for all tools —
  OPS-001
- **CI separation**: default job runs `pytest -m "not live"` (no
  network); live tests run only on `main` pushes and
  `workflow_dispatch` — OPS-001
- Multi-tenant warning in cloud-deployment sections — SEC-009
- Audit findings under `audits/2026-05-27T120439-Z-wsl-envidat-mcp/`

### Changed

- **Error handling (OBS-001):** Tool failures now raise `ToolError`
  instead of returning a plain error string. FastMCP propagates this as
  `CallToolResult.isError=True`, so MCP clients can finally distinguish
  success from failure.
- **`MCP_TRANSPORT`** value: canonical form is now `streamable-http`
  (hyphen); the legacy `streamable_http` is still accepted for
  backwards compatibility.
- **`pyproject.toml`**: `mcp>=1.3.0,<2.0.0` upper-bound; `structlog`,
  `respx` added.

### Fixed

- **Latent crash in `streamable-http` path:** the old `main()` called
  `mcp.run(transport="streamable_http", port=port)` which raised
  `TypeError` (no `port=` kwarg on `FastMCP.run`) and used a non-SDK
  transport string. The cloud-deployment path was broken on `main`
  before this release.

## [0.1.0] - 2026-03-13

### Added
- 12 tools for EnviDat CKAN API access
  - `wsl_search_datasets` — Full-text search across 1,000+ datasets
  - `wsl_get_dataset` — Full metadata incl. DOI and download URLs
  - `wsl_search_by_domain` — Thematic search (5 WSL research domains)
  - `wsl_search_by_location` — Spatial search via bounding box
  - `wsl_list_organizations` — List WSL research units
  - `wsl_get_organization` — Research unit details
  - `wsl_list_tags` — Browse tags/keywords
  - `wsl_get_recent_datasets` — Most recently updated datasets
  - `wsl_get_avalanche_data` — SLF avalanche & snow data
  - `wsl_get_forest_data` — Forest data incl. LFI and Sanasilva
  - `wsl_get_naturgefahren_data` — Natural hazard datasets
  - `wsl_catalog_stats` — Catalog overview and statistics
- 2 MCP resources
  - `envidat://organization/{name}` — Organization as resource
  - `envidat://domain/{domain}` — Domain overview as resource
- Dual transport: stdio (Claude Desktop) + Streamable HTTP (cloud)
- Bilingual documentation: English primary (README.md) + German (README.de.md)
- 11 live API integration tests (11/11 passing)
- GitHub Actions CI (Python 3.11–3.13)
