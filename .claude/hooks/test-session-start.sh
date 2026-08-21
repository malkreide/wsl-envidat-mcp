#!/usr/bin/env bash
#
# Gegenprobe-Harness fuer .claude/hooks/session-start.sh
#
# Baut echte Git-Repos in einem Temp-Verzeichnis und faehrt den Hook gegen
# jeden Fall, der ihn zum Blockieren oder zum Falschalarm bringen koennte.
# Kein Netzzugang noetig -- alle "Remotes" sind lokale Pfade.
#
#   bash .claude/hooks/test-session-start.sh
#
# Laeuft NICHT in der CI (ci.yml prueft nur Python; ruff und pytest sehen
# .claude/ nicht). Nach jeder Aenderung am Hook von Hand ausfuehren.
#
# Ein gruener Lauf allein beweist nichts: die Zusicherungen wurden einzeln
# neutralisiert, um zu zeigen, dass genau die zugehoerigen Faelle fallen.
# Siehe README.md, Abschnitt «Gegenprobe».
HOOK="${HOOK:-$(cd "$(dirname "$0")" && pwd)/session-start.sh}"
W=$(mktemp -d); : > "$W/gitconfig"
export GIT_CONFIG_GLOBAL="$W/gitconfig" GIT_CONFIG_SYSTEM="$W/gitconfig"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t.t
export GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t.t
pass=0; fail=0

run() { # run <dir> -> setzt OUT/RC
  OUT=$(cd "$1" && CLAUDE_PROJECT_DIR="$1" timeout 30 "$HOOK" 2>&1); RC=$?
}
check() { # check <name> <erwartet: silent|report> [muster]
  local name=$1 want=$2 pat=${3:-}
  local ok=1
  [ "$RC" -eq 0 ] || ok=0
  if [ "$want" = silent ]; then
    [ -z "$OUT" ] || ok=0
  else
    printf '%s' "$OUT" | grep -q "$pat" || ok=0
  fi
  if [ $ok -eq 1 ]; then echo "  PASS  $name"; pass=$((pass+1))
  else echo "  FAIL  $name (rc=$RC, out=[${OUT:0:120}])"; fail=$((fail+1)); fi
}

mkorigin() { # mkorigin <pfad> <branchname> <n-commits>
  git init -q -b "$2" "$1"; local i
  for i in $(seq 1 "$3"); do
    echo "$i" > "$1/f$i"; git -C "$1" add -A; git -C "$1" commit -qm "c$i"
  done
}

echo "== 1. Default-Branch 'main', 3 Commits zurueck =="
mkorigin "$W/o1" main 5
git clone -q "$W/o1" "$W/c1"; git -C "$W/c1" reset -q --hard HEAD~3
run "$W/c1"; check "meldet 3 Commits" report "liegt 3 Commits hinter origin/main"

echo "== 2. Default-Branch 'master' (NICHT main) =="
mkorigin "$W/o2" master 5
git clone -q "$W/o2" "$W/c2"; git -C "$W/c2" reset -q --hard HEAD~2
run "$W/c2"; check "meldet gegen origin/master" report "hinter origin/master"
check "nennt nirgends 'main'" report "master"
printf '%s' "$OUT" | grep -q "origin/main" && { echo "  FAIL  raet auf main"; fail=$((fail+1)); } || { echo "  PASS  raet nicht auf main"; pass=$((pass+1)); }

echo "== 3. Aktueller Stand -> schweigt =="
git clone -q "$W/o1" "$W/c3"
run "$W/c3"; check "schweigt bei 0" silent

echo "== 4. Genau 1 Commit -> Singular =="
git clone -q "$W/o1" "$W/c4"; git -C "$W/c4" reset -q --hard HEAD~1
run "$W/c4"; check "Singular 'Commit'" report "1 Commit hinter"

echo "== 5. Remote weg (Netz/DNS-Ausfall simuliert) =="
git clone -q "$W/o1" "$W/c5"; git -C "$W/c5" reset -q --hard HEAD~3
rm -rf "$W/o1"
run "$W/c5"; check "still durch, exit 0" silent

echo "== 6. Kein Remote origin =="
mkorigin "$W/c6" main 2
run "$W/c6"; check "still durch" silent

echo "== 7. Kein Git-Arbeitsbaum =="
mkdir -p "$W/plain"
run "$W/plain"; check "still durch" silent

echo "== 8. Detached HEAD, 2 zurueck =="
mkorigin "$W/o8" main 5
git clone -q "$W/o8" "$W/c8"; git -C "$W/c8" checkout -q --detach HEAD~2
run "$W/c8"; check "meldet trotz detached" report "hinter origin/main"

echo "== 9. Unverbundene Historie =="
mkorigin "$W/o9" main 3
git clone -q "$W/o9" "$W/c9"
git -C "$W/c9" checkout -q --orphan waise; git -C "$W/c9" rm -rq --cached . 2>/dev/null
echo x > "$W/c9/x"; git -C "$W/c9" add -A; git -C "$W/c9" commit -qm waise
run "$W/c9"; check "still durch (kein merge-base)" silent

echo "== 10. Flacher Klon, Grenze verdeckt den merge-base =="
mkorigin "$W/o10" main 8
git clone -q --depth 1 "file://$W/o10" "$W/c10"
run "$W/c10"; check "still durch statt Falschalarm" silent

echo "== 11. Unerreichbarer Remote-Host (haengendes Netz) =="
git clone -q "$W/o8" "$W/c11"; git -C "$W/c11" reset -q --hard HEAD~2
git -C "$W/c11" remote set-url origin https://10.255.255.1/nope.git
start=$SECONDS; run "$W/c11"; dauer=$((SECONDS-start))
check "still durch" silent
[ "$dauer" -le 20 ] && { echo "  PASS  Timeout greift (${dauer}s)"; pass=$((pass+1)); } || { echo "  FAIL  zu langsam (${dauer}s)"; fail=$((fail+1)); }

echo "== 12. Flacher Klon (depth 1), danach eilt origin voraus  [Web-Normalfall] =="
mkorigin "$W/o12" main 4
git clone -q --depth 1 "file://$W/o12" "$W/c12"
for i in 5 6 7; do echo $i > "$W/o12/f$i"; git -C "$W/o12" add -A; git -C "$W/o12" commit -qm "c$i"; done
run "$W/c12"; check "meldet 3 trotz flachem Klon" report "liegt 3 Commits hinter origin/main"

echo "== 13. Flacher Klon, divergent -> zaehlt wie ein voller Klon =="
mkorigin "$W/o13" main 6
git clone -q --depth 1 "file://$W/o13" "$W/c13"
echo eigen > "$W/c13/eigen"; git -C "$W/c13" add -A; git -C "$W/c13" commit -qm eigen
for i in 7 8; do echo $i > "$W/o13/f$i"; git -C "$W/o13" add -A; git -C "$W/o13" commit -qm "c$i"; done
run "$W/c13"; check "meldet 2 trotz flachem Klon + eigenem Commit" report "liegt 2 Commits hinter origin/main"

echo "== 14. Voller Klon, divergent -> meldet die fehlenden Commits =="
mkorigin "$W/o14" main 4
git clone -q "$W/o14" "$W/c14"
echo eigen > "$W/c14/eigen"; git -C "$W/c14" add -A; git -C "$W/c14" commit -qm eigen
for i in 5 6; do echo $i > "$W/o14/f$i"; git -C "$W/o14" add -A; git -C "$W/o14" commit -qm "c$i"; done
run "$W/c14"; check "meldet 2" report "liegt 2 Commits hinter origin/main"

echo; echo "PASS=$pass FAIL=$fail"; rm -rf "$W"; [ "$fail" -eq 0 ]
