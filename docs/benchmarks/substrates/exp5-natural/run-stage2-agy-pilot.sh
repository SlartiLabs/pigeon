#!/usr/bin/env bash
# Stage 2 (cross-model) pilot — recoverability side, receiver swapped to agy/Gemini.
#
# Self-contained: builds a fresh throwaway git repo from THIS committed Exp-5
# substrate (no /tmp/bench pre-setup needed), then runs N trials of one arm and
# grades each with the held-out accept.py. The architect hop stays on sonnet
# (it is the only hop that could run shell); to_wire/from_wire are pure-edit agy.
#
# Usage:
#   bash run-stage2-agy-pilot.sh [N] [arm]
#     N    trial count           (default 1 — a true pilot; the plan's confirm is N=12)
#     arm  pointers-only-agy | with-derived-agy   (default pointers-only-agy)
#
# First run this at N=1 to confirm the mechanism fires end to end (GATE C), read
# the printed per-trial cost, THEN scale to N=12 per arm for the confirm tier.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$(cd "$HERE/../../../.." && pwd)"            # repo root (for .pigeon/config + schema)
N="${1:-1}"
ARM="${2:-pointers-only-agy}"
TASKS="$HERE/${ARM}.tasks.json"
[ -f "$TASKS" ] || { echo "no such arm: $TASKS" >&2; exit 2; }
command -v agy   >/dev/null || { echo "agy not on PATH"    >&2; exit 2; }
command -v claude>/dev/null || { echo "claude not on PATH" >&2; exit 2; }

WORK="$(mktemp -d)"; REPO="$WORK/repo"
mkdir -p "$REPO/ledger" "$REPO/tests" "$REPO/.pigeon"
cp "$HERE/account.py"        "$REPO/ledger/account.py"
: > "$REPO/ledger/__init__.py"
cp "$HERE/TASK.md"           "$REPO/TASK.md"
cp "$HERE/test_account.py"   "$REPO/tests/test_account.py"
cp "$TASKS"                  "$REPO/$ARM.tasks.json"
cp "$HERE/accept.py"         "$WORK/accept.py"        # held OUT of the agent tree
# Reuse the proven runner defs + 1.2 handoff schema from the main repo verbatim.
cp "$MAIN/.pigeon/config.yaml"        "$REPO/.pigeon/config.yaml"
cp "$MAIN/.pigeon/handoff.schema.json" "$REPO/.pigeon/handoff.schema.json"
grep -q '"derived"' "$REPO/.pigeon/handoff.schema.json" || { echo "schema not 1.2" >&2; exit 3; }

git -C "$REPO" init -q
git -C "$REPO" add ledger tests TASK.md "$ARM.tasks.json" .pigeon/config.yaml .pigeon/handoff.schema.json
git -C "$REPO" -c user.email=s2@local -c user.name=s2 commit -q -m pristine

OUT="$WORK/results"; mkdir -p "$OUT"
RES="$OUT/results.csv"; echo "trial,arm,accept_rc,turns,cost_usd,wall_s,agy_fired,injected,read_cue" > "$RES"

for i in $(seq 1 "$N"); do
  rdir="$OUT/t$i"; mkdir -p "$rdir"
  git -C "$REPO" reset --hard -q HEAD
  rm -rf "$REPO/.pigeon/handoffs" "$REPO/.pigeon/context" "$REPO/.pigeon/coordinate" "$REPO/.pigeon/metrics.jsonl"
  # pristine guard: the added defs must not exist yet
  defs=$(grep -c 'def to_wire\|def from_wire' "$REPO/ledger/account.py")
  [ "$defs" -ne 0 ] && { echo "ABORT: not pristine before t$i (defs=$defs)" >&2; exit 4; }

  t0=$(date +%s)
  ( cd "$REPO" && timeout -k 30 900 pigeon coordinate "$ARM.tasks.json" \
      --skip-permissions --telemetry --budget-usd 3 ) > "$rdir/run" 2>&1
  wall=$(( $(date +%s) - t0 ))

  PYTHONPATH="$REPO" python "$WORK/accept.py" > "$rdir/accept" 2>&1; arc=$?
  man="$(ls -t "$REPO"/.pigeon/coordinate/runs/*.json 2>/dev/null | head -1)"
  cp "$man" "$rdir/manifest.json" 2>/dev/null
  turns=$(python - "$man" <<'PY' 2>/dev/null || echo NA
import json,sys
d=json.load(open(sys.argv[1]))
print(sum((t.get("telemetry") or {}).get("num_turns",0) for t in d["tasks"].values()))
PY
)
  cost=$(python - "$man" <<'PY' 2>/dev/null || echo NA
import json,sys
d=json.load(open(sys.argv[1]))
print(round(sum((t.get("telemetry") or {}).get("total_cost_usd",0) for t in d["tasks"].values()),4))
PY
)
  # mechanism: did the agy receiver hop actually run, get the injection, read the cue?
  logdir="$REPO/.pigeon/coordinate/logs"
  agy_fired=$(find "$logdir" -name '*to_wire.log' -size +0c 2>/dev/null | head -1 | grep -c . )
  injected=$(grep -l "Carried reasoning" "$logdir"/*to_wire.log 2>/dev/null | wc -l)
  read_cue=$(grep -li "to_legacy\|legacy" "$logdir"/*to_wire.log "$logdir"/*from_wire.log 2>/dev/null | wc -l)
  echo "$i,$ARM,$arc,$turns,$cost,$wall,$agy_fired,$injected,$read_cue" >> "$RES"
  echo "[t$i] accept_rc=$arc turns=$turns cost=\$$cost ${wall}s agy_fired=$agy_fired injected=$injected read_cue=$read_cue"
done

echo "=== STAGE 2 PILOT ($ARM, N=$N) ==="
echo "PASS (accept_rc==0): $(awk -F, 'NR>1 && $3==0' "$RES" | wc -l)/$N"
echo "artifacts: $WORK   (results.csv, per-trial run/accept/manifest)"
echo "NOTE: agy telemetry is unmeasured (telemetry_flags.agy=[]), so cost_usd reflects the sonnet architect hop only — the receiver-side USD asymmetry is itself a Stage 2 finding to record."
cat "$RES"
