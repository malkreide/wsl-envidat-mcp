# Use Cases & Examples — wsl-envidat-mcp

Praxisnahe Anfragen nach Zielgruppe an die Umweltforschungs- und Monitoringdaten der WSL (Eidg. Forschungsanstalt für Wald, Schnee und Landschaft) via EnviDat. **Kein API-Key erforderlich** — alle Daten sind offen zugänglich (CKAN-API von envidat.ch).

## 🏫 Bildung & Schule

**«Wir behandeln im Unterricht den Schweizer Wald — welche aktuellen Forschungsdaten zum Waldzustand gibt es?»**
**API-Key nötig:** Nein
→ `wsl_get_forest_data(limit=8)`
→ `wsl_search(domain="wald", limit=10)`
Warum nützlich: Liefert echte Datensätze aus dem Landesforstinventar (LFI) und dem Sanasilva-Waldschadensmonitoring — belastbares Anschauungsmaterial statt Lehrbuchgrafiken.

**«Für ein Geografie-Projekt suchen wir Datensätze rund um unseren Schulstandort im Kanton Zürich.»**
**API-Key nötig:** Nein
→ `wsl_search(bbox=[8.35, 47.15, 8.98, 47.72], limit=10)`
Warum nützlich: Die Bounding-Box-Suche filtert Forschungsdaten geografisch auf die Region — Schüler:innen recherchieren ortsbezogen statt abstrakt.

**«Was passiert eigentlich bei Lawinen? Gibt es echte Messreihen für den Physikunterricht?»**
**API-Key nötig:** Nein
→ `wsl_get_avalanche_data(limit=6)`
→ `wsl_get_dataset(id_or_slug="fatal-avalanche-accidents-in-switzerland-since-1936-37")`
Warum nützlich: SLF-Schneemessreihen und die Unfalldatenbank seit 1936/37 machen Statistik, Wahrscheinlichkeit und Naturgefahren im Unterricht greifbar.

## 👨‍👩‍👧 Eltern & Schulgemeinde

**«Ist der geplante Schulweg / Standort durch Naturgefahren wie Rutschungen oder Steinschlag betroffen?»**
**API-Key nötig:** Nein
→ `wsl_get_naturgefahren_data(limit=8)`
→ `wsl_search(domain="naturgefahren", limit=10)`
Warum nützlich: WSL-Naturgefahrendaten (Murgänge, Rutschungen, Steinschlag, Hochwasser) sind eine sachliche Grundlage für Standort- und Sicherheitsfragen im Elterngremium.

**«Wie steht es um die Trockenheit und den Zustand der Bäume rund um unser Quartier?»**
**API-Key nötig:** Nein
→ `wsl_search(domain="landschaft", query="drought", limit=8)`
→ `wsl_get_forest_data(limit=6)`
Warum nützlich: Verbindet Dürre- und Landschaftsdaten mit Waldzustandsdaten — hilfreich für Diskussionen über Hitzeinseln, Baumpflanzungen und Pausenplatzgestaltung.

## 🗳️ Bevölkerung & öffentliches Interesse

**«Welche Forschungseinheiten der WSL publizieren Daten, und wer ist für Lawinenforschung zuständig?»**
**API-Key nötig:** Nein
→ `wsl_list_organizations()`
→ `wsl_get_organization(name="slf", include_datasets=true)`
Warum nützlich: Schafft Transparenz darüber, wer welche öffentlich finanzierten Umweltdaten erhebt — vom SLF (Schnee & Lawinen) bis zu den Waldforschungsgruppen.

**«Was gibt es Neues aus der Schweizer Umweltforschung?»**
**API-Key nötig:** Nein
→ `wsl_get_recent_datasets(limit=10)`
→ `wsl_catalog_stats()`
Warum nützlich: Zeigt die zuletzt aktualisierten Datensätze plus eine Katalog-Übersicht (Anzahl Datensätze pro Domäne, Top-Forschungseinheiten) — ein niederschwelliger Einstieg für Interessierte.

## 🤖 KI-Interessierte & Entwickler:innen

**«Ich möchte einen präzisen Suchbegriff finden, bevor ich den Katalog abfrage.»**
**API-Key nötig:** Nein
→ `wsl_list_tags(query="snow", limit=50)`
→ `wsl_search(query="snowpack", organization="slf", limit=10)`
Warum nützlich: Da die Solr-Suche `OR` als Stopwort behandelt, hilft die Tag-Liste, präzise Einzelbegriffe zu wählen — robustere, reproduzierbare Abfragen für Daten-Pipelines.

**«Ich baue eine "Lage-Übersicht" für eine Zürcher Schulhaus-Umgebung und kombiniere Umwelt- mit Stadtdaten.»**
**API-Key nötig:** Nein
→ `wsl_search(bbox=[8.35, 47.15, 8.98, 47.72], domain="wald", limit=10)` (WSL-Waldzustand)
→ kombiniert mit `zurich-opendata-mcp` → `zurich_air_quality()` und `zurich_geo_features(layer_id="schulanlagen")`
Warum nützlich: Portfolio-Kombination — WSL-Waldzustand und Naturgefahren plus die städtische Luftqualität und Schulanlagen-Geodaten aus `zurich-opendata-mcp` ergeben eine integrierte Umgebungsanalyse.

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|---|---|---|
| Frei im Katalog suchen (Stichwort, Domäne, Organisation, Bounding-Box kombinierbar) | `wsl_search` | Nein |
| Alle Metadaten, DOI und Download-Links eines Datensatzes ansehen | `wsl_get_dataset` | Nein |
| Wissen, welche WSL-Forschungseinheiten Daten publizieren | `wsl_list_organizations` | Nein |
| Details und Datensätze einer Einheit (z. B. `slf`) abrufen | `wsl_get_organization` | Nein |
| Passende Schlagwörter für präzise Suchen finden | `wsl_list_tags` | Nein |
| Die neusten Datensätze entdecken (Monitoring) | `wsl_get_recent_datasets` | Nein |
| Lawinen- und Schneedaten des SLF abfragen | `wsl_get_avalanche_data` | Nein |
| Walddaten inkl. Landesforstinventar (LFI) & Sanasilva abfragen | `wsl_get_forest_data` | Nein |
| Naturgefahrendaten (Rutschung, Steinschlag, Hochwasser) abfragen | `wsl_get_naturgefahren_data` | Nein |
| Eine Katalog-Übersicht mit Statistiken erhalten | `wsl_catalog_stats` | Nein |

Gültige Domänen für `wsl_search(domain=…)`: `wald`, `biodiversitaet`, `naturgefahren`, `schnee_eis`, `landschaft`.
