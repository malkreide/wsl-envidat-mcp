# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-07** von `https://www.envidat.ch/api/action`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

**Es sind Ausschnitte, keine Vollabzuege.** Wo gekuerzt wurde, bleiben
die Zaehlfelder (`count`, `package_count`) auf dem echten Wert.

**Tags stehen in der Schreibweise der Quelle** — EnviDat fuehrt sie in
GROSSBUCHSTABEN. Sie kleinzuschreiben wuerde eine Eigenschaft
wegputzen, die im Repo sichtbar bleiben soll; die Tag-*Suche* ist
upstream case-insensitiv, die ausgelieferten *Werte* sind es nicht.

## `package_search.json`

- **Quelle:** `https://www.envidat.ch/api/action/package_search?rows=2`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** 2 Datensaetze; `count` ist der echte Gesamtbestand (858)
- **Groesse:** 27061 B
- **SHA-256:** `c6469c79e3812776e9347a6a474524bd00ad36d2acb04bef2c0fc8651b8fd258`

## `package_show.json`

- **Quelle:** `https://www.envidat.ch/api/action/package_show?id=fatal-avalanche-accidents-in-switzerland-since-1936-37`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** vollstaendig, 42 Felder (die handgeschriebene Vorgaengerin hatte 9); 5 Tags, so geschrieben wie die Quelle sie fuehrt
- **Groesse:** 13274 B
- **SHA-256:** `aafb557c7aae07638ad23adb7b1a80d0a8a18bbf0adc32658918e4d406aa68a9`

## `organization_list.json`

- **Quelle:** `https://www.envidat.ch/api/action/organization_list?all_fields=true`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** vollstaendig, 25 Organisationen
- **Groesse:** 36383 B
- **SHA-256:** `00009991ae0897e5876633d2de3bbdc94f4a055602392e3e9c219982ec9fbc82`

## `organization_show.json`

- **Quelle:** `https://www.envidat.ch/api/action/organization_show?id=avalanche-formation&include_datasets=true`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** Organisation «avalanche-formation»; `packages` auf die ersten 2 von 10 gekuerzt, `package_count` unveraendert (19)
- **Groesse:** 25038 B
- **SHA-256:** `cf8c46c96530fe0ed9aff956ddc06e7b1d6b8a409a1b84928ef6bdd1196a92cf`

## `tag_list.json`

- **Quelle:** `https://www.envidat.ch/api/action/tag_list?query=snow`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** die ersten 8 von 114 Tags zu «snow», in der Schreibweise der Quelle
- **Groesse:** 252 B
- **SHA-256:** `d8499c8c870cce048c100a6fa1947a7aa8832debc7916e45113e2fc96e48ecb4`
