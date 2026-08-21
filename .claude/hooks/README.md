# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<default-branch>` liegt. Liegt er nicht
zurück, schweigt der Hook.

## Grund

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Die Prüfung kostet eine
Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.

Das ist der teure Fehlermodus: Der Diff ist korrekt, die lokalen Gates sind
grün, und die CI meldet einen Fehler, für den es im geänderten Code keine
Entsprechung gibt. Wer die Ursache im Diff sucht, sucht am falschen Ort. Der
Hook macht die Differenz sichtbar, bevor die Arbeit beginnt.

## Oberste Regel: der Hook blockiert nie

Ein Hook, der bei Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal
abgeschaltet und schützt danach gar nichts. Deshalb geht **jeder** der
folgenden Fälle still durch — kein Output, Exit-Code 0:

| Fall | Verhalten |
| --- | --- |
| Kein Netz / DNS flattert / Remote nicht erreichbar | `timeout` greift, still durch |
| Kein Remote `origin` | still durch |
| Kein Git-Arbeitsbaum | still durch |
| Flacher Klon (`--depth`) | zählt normal — siehe unten |
| Detached HEAD | funktioniert normal; ohne gemeinsamen Vorfahren still durch |
| Default-Branch nicht ermittelbar | still durch — **nie** auf `main` geraten |
| `git` oder `timeout` fehlen | still durch |
| Stand ist aktuell (0 Commits) | still durch |

Die ersten beiden Prüfungen (Arbeitsbaum, `origin`) sowie die Zahl-Validierung
vor der Ausgabe sind bewusst **redundant**: fällt eine weg, fängt ein späterer
Guard denselben Fall ab. Sie sind daher durch keinen Testfall einzeln
falsifizierbar. Sie bleiben trotzdem drin — «blockiert nie» ist Anforderung
Nummer eins, und sie kosten nichts.

Konkret umgesetzt durch:

- **kein `set -e`.** Ein einzelner fehlschlagender `git`-Aufruf darf das
  Skript nicht mit != 0 beenden. Jeder Pfad endet explizit in `exit 0`.
- **`exec 2>/dev/null`.** git-Diagnostik ist hier Rauschen.
- **Timeout auf jedem Netzaufruf** (`ls-remote` und `fetch`), Vorgabe 5
  Sekunden, überschreibbar per `CLAUDE_STALE_CLONE_TIMEOUT`. Zusätzlich
  deckelt `settings.json` den Hook bei 15 Sekunden.
- **`GIT_TERMINAL_PROMPT=0`** plus `GIT_ASKPASS` / `SSH_ASKPASS` /
  `ssh -oBatchMode=yes`. Ein Passwort-Prompt im Sessionstart wäre genau das
  Hängen, das der Hook vermeiden soll — bei HTTPS-Remotes ohne gültige
  Credentials ist das der wahrscheinlichste Aufhänger.

## Default-Branch wird ermittelt, nicht angenommen

Drei Server im Portfolio (`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`)
nennen ihren Default-Branch `master`. Ein fest verdrahtetes `origin/main`
scheitert dort mit «couldn't find remote ref main» — was leicht für ein
Netzproblem gehalten wird. Genau diese Annahme hat schon einmal einen Branch
15 Commits alt werden lassen.

Die Ermittlung läuft in drei Stufen, billigste zuerst:

1. `git symbolic-ref refs/remotes/origin/HEAD` — lokal hinterlegt, kein Netz.
   In frischen Klonen oft **nicht** gesetzt, deshalb reicht das allein nicht.
2. `git ls-remote --symref origin HEAD` — autoritativ, netzabhängig, gedeckelt.
3. Ein bereits bekannter `origin/main` bzw. `origin/master`.

Bleibt der Branch leer, endet der Hook still. Auf `main` zu raten würde
entweder einen Fehler erzeugen oder — schlimmer — eine falsche Entwarnung.

Der `:?`-Schutz aus `CLAUDE.md` ist im Skript durch die Leerprüfung vor dem
Fetch ersetzt: Bei leerem Branch fetcht git sonst still den Remote-HEAD und
endet mit 0.

## Flache Klone brauchen keine Sonderbehandlung

Claude Code auf dem Web klont flach — dieser Klon hier ist es auch. Trotzdem
zählt der Hook korrekt: `HEAD..origin/<branch>` läuft von `origin/<branch>`
nur bis zum gemeinsamen Vorfahren und besucht dessen Vorfahren nie.

Nachgemessen gegen volle Klone in den Tiefen 1, 2 und 3 — identische Zahlen,
auch wenn der merge-base genau auf der Shallow-Grenze liegt. Das muss so
sein: der tiefste gemeinsame Vorfahre kann nicht *unterhalb* eines bereits
bekannten gemeinsamen Vorfahren liegen.

Ein erster Entwurf stieg bei flachen Klonen pauschal aus. Das hätte den Hook
in genau der Umgebung stillgelegt, für die er gedacht ist. Wer die Sperre
wieder einbauen will: erst nachmessen.

## Prüfen

```bash
bash .claude/hooks/test-session-start.sh
```

17 Fälle, kein Netzzugang nötig (alle «Remotes» sind lokale Pfade). Erwartung:
`PASS=17 FAIL=0`. Einzellauf gegen das echte Repo:

```bash
.claude/hooks/session-start.sh; echo "exit=$?"
```

Auf aktuellem Stand: keine Ausgabe, `exit=0`.

## Gegenprobe

Ein grüner Lauf beweist nichts, solange die Tests auch ohne die
Implementierung grün bleiben. Jede Zusicherung wurde einzeln neutralisiert;
es fallen genau die zugehörigen Fälle:

| Neutralisiert | Es fällt |
| --- | --- |
| Default-Branch fest auf `main` verdrahtet | Fall 2 (`master`-Repo) — meldet nichts mehr |
| `merge-base`-Prüfung entfernt | Fall 9 (unverbundene Historie) — Falschalarm «3 Commits» |
| Schweigen bei 0 entfernt | Fälle 3 und 10 — meldet «0 Commits hinter» |
| Beide `timeout` entfernt | Fall 11 hängt bis zum Abbruch von aussen (rc=124) |

Der Timeout wurde am echten Aufhänger gemessen, nicht an einem Remote, der
schnell scheitert: `GIT_SSH_COMMAND` auf ein Skript, das 120 s schläft. Mit
Deckel endet der Hook nach 5 s still, ohne Deckel hängt er.

Nicht falsifizierbar sind die drei redundanten Guards (siehe oben) — das ist
Absicht, keine Testlücke.

## CI

Der Hook ist **nicht** Teil der Gates. `ci.yml` prüft `src/`, `tests/` und
`scripts/`; `ruff` und `pytest` sehen `.claude/` nicht, und Bash prüft dort
kein Gate. Änderungen deshalb von Hand mit `bash -n` und dem Harness oben
verifizieren.
