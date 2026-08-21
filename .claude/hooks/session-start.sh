#!/usr/bin/env bash
#
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<default-branch> liegt.
#
# GRUND: Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt,
# deren Ursache nicht im Diff stand — die fehlenden Commits waren jeweils
# genau die, die das Gate einfuehrten, an dem der Branch scheiterte. Die
# Pruefung kostet eine Sekunde und ersetzt eine Fehlersuche in den falschen
# Dateien. Ausfuehrlich: .claude/hooks/README.md
#
# OBERSTE REGEL: Dieser Hook blockiert die Session NIEMALS. Kein Netz, kein
# Remote, detached HEAD, flatterndes DNS, flacher Klon — jeder dieser Faelle
# geht still durch (exit 0, keine Ausgabe). Ein Hook, der bei Netzproblemen
# die Arbeit anhaelt, wird nach dem zweiten Mal abgeschaltet und schuetzt
# danach gar nichts.
#
# Deshalb bewusst KEIN `set -e`: ein einzelner fehlschlagender git-Aufruf
# darf das Skript nicht mit != 0 beenden. Jeder Pfad endet in `exit 0`.

set -u

# Netz-Timeout in Sekunden. Bewusst klein: der Sessionstart darf nicht haengen.
readonly FETCH_TIMEOUT="${CLAUDE_STALE_CLONE_TIMEOUT:-5}"

# Jede Ausgabe auf stderr unterdruecken -- Diagnostik von git ist hier Rauschen.
exec 2>/dev/null

# `timeout` fehlt (kein coreutils)? Dann lieber gar nicht fetchen, als ohne
# Deckel ins Netz zu greifen.
command -v timeout >/dev/null || exit 0
command -v git >/dev/null || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Kein Git-Arbeitsbaum -> nichts zu pruefen.
[ "$(git rev-parse --is-inside-work-tree)" = "true" ] || exit 0

# Kein Remote `origin` -> nichts abzugleichen.
git remote get-url origin >/dev/null || exit 0

# git darf unter keinen Umstaenden interaktiv nach Zugangsdaten fragen --
# ein Passwort-Prompt im Sessionstart ist genau das Haengen, das wir vermeiden.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true
export SSH_ASKPASS=/bin/true
export SSH_ASKPASS_REQUIRE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes}"

# --- Default-Branch ermitteln, nicht als "main" annehmen. -------------------
# Mindestens ein Repo im Portfolio nutzt "master"; genau diese Annahme hat
# schon einmal einen Branch 15 Commits alt werden lassen, weil ein fest
# verdrahtetes origin/main mit «couldn't find remote ref main» scheiterte.

branch=""

# 1. Lokal hinterlegter Remote-HEAD -- kostet kein Netz.
branch="$(git symbolic-ref --short refs/remotes/origin/HEAD)"
branch="${branch#origin/}"

# 2. Remote fragen. Autoritativ, aber netzabhaengig -> gedeckelt.
if [ -z "$branch" ]; then
  branch="$(timeout "$FETCH_TIMEOUT" git ls-remote --symref origin HEAD |
    sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')"
fi

# 3. Letzter Ausweg: ein bereits bekannter Remote-Branch der ueblichen Namen.
if [ -z "$branch" ]; then
  for candidate in main master; do
    if git rev-parse --verify --quiet "refs/remotes/origin/$candidate" >/dev/null; then
      branch="$candidate"
      break
    fi
  done
fi

# Nicht ermittelbar -> still durchgehen. Niemals auf "main" raten: das
# erzeugt entweder einen Fehler oder, schlimmer, eine falsche Entwarnung.
[ -n "$branch" ] || exit 0

# --- Aktuellen Remote-Stand holen. ------------------------------------------
# Der `:?`-Schutz aus CLAUDE.md ist hier durch die Leerpruefung oben ersetzt:
# bei leerem Branch fetcht git sonst still den Remote-HEAD und endet mit 0.
timeout "$FETCH_TIMEOUT" git fetch --quiet origin "$branch" || exit 0

# Ohne gemeinsamen Vorfahren waere die Zahl bedeutungslos (unverbundene
# Historien, verwaister HEAD, oder ein flacher Klon, dessen Remote-Historie
# nach dem Fetch nicht bis zu HEAD zurueckreicht).
#
# Ein flacher Klon (Claude Code auf dem Web klont so) braucht sonst KEINE
# Sonderbehandlung: die Zaehlung laeuft von origin/<branch> nur bis zum
# gemeinsamen Vorfahren und dessen Vorfahren werden nie besucht. Nachgemessen
# gegen volle Klone in den Tiefen 1/2/3 -- identische Zahlen, auch wenn der
# merge-base genau auf der Shallow-Grenze liegt. Das muss so sein: der
# tiefste gemeinsame Vorfahre kann nicht unterhalb eines bereits bekannten
# gemeinsamen Vorfahren liegen.
git merge-base HEAD "origin/$branch" >/dev/null || exit 0

behind="$(git rev-list --count "HEAD..origin/$branch")"

# Kein Ergebnis oder keine reine Zahl (z. B. unverbundene Historien,
# detached HEAD ohne gemeinsamen Vorfahren) -> still durchgehen.
case "$behind" in
  '' | *[!0-9]*) exit 0 ;;
esac

# Ausgabe NUR, wenn tatsaechlich Commits fehlen. Bei 0 schweigt der Hook.
[ "$behind" -gt 0 ] || exit 0

commit_wort="Commits"
[ "$behind" -eq 1 ] && commit_wort="Commit"

# stdout eines SessionStart-Hooks landet im Kontext der Session.
cat <<MSG
[Klon-Aktualitaet] Der ausgecheckte Stand liegt $behind $commit_wort hinter origin/$branch.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht:
die fehlenden Commits sind erfahrungsgemaess genau die, die das Gate
einfuehren, an dem der Branch scheitert. Vor dem Arbeiten angleichen:

    git merge origin/$branch     # oder: git rebase origin/$branch

Falls die CI ohne erkennbaren Grund rot ist, ist das hier der erste Verdacht.
MSG

exit 0
