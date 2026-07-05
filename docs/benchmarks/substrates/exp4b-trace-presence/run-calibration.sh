#!/usr/bin/env bash
# Exp-4b Stage-1 calibration: pointers-only (the R meter), N per variant, across the
# R ladder {R_low, R_mid, R_high}. Stages each variant into its own git worktree from
# the Exp-5 scaffold (which carries the .pigeon sonnet-runner config), swapping in only
# account.py / tests / TASK.md / the arm spec. Pristine guard = ADDED defs (to_wire/
# from_wire), NOT the keys (R_mid/R_high legitimately contain them).
#
# Usage:  run-calibration.sh [N] [variant ...]
#   N         trials per variant (default 4 = prereg Stage-1 calibration N)
#   variant   subset of: R_low R_mid R_high (default all three)
set -u
SUB="$(cd "$(dirname "$0")" && pwd)"          # the committed substrate dir
SCAF=/tmp/bench/exp5/wt-pointers              # proven pigeon scaffold (config+git+pkg)
B=/tmp/bench/exp4b
N="${1:-4}"; shift || true
VARIANTS=("${@:-R_low R_mid R_high}"); VARIANTS=(${VARIANTS[@]})
mkdir -p "$B/results"
SUMMARY="$B/results/calibration-summary.csv"
echo "variant,trial,accept_rc,num_turns,cost_usd,wall_s,read_cue" > "$SUMMARY"

stage() {  # $1=variant -> fresh worktree at $B/wt-$1 with the variant swapped in
  local V="$1" WT="$B/wt-$V"
  rm -rf "$WT"; mkdir -p "$WT/ledger" "$WT/tests"
  # scaffold: pigeon config, schema, package metadata, canonical doc
  cp -r "$SCAF/.pigeon" "$WT/.pigeon"; rm -rf "$WT/.pigeon/handoffs" "$WT/.pigeon/context" \
        "$WT/.pigeon/coordinate" "$WT/.pigeon/metrics.jsonl" "$WT/.pigeon/manifest.json" 2>/dev/null
  cp "$SCAF/pyproject.toml" "$WT/pyproject.toml"
  cp "$SCAF/AGENTS.md" "$WT/AGENTS.md" 2>/dev/null || true
  cp "$SCAF/ledger/__init__.py" "$WT/ledger/__init__.py"
  : > "$WT/tests/__init__.py" 2>/dev/null || true
  # the variant-specific bits (copy ALL ledger modules so distant-cue variants
  # like R_mid2 carry their sibling codec, not just account.py)
  cp "$SUB/$V"/ledger/*.py "$WT/ledger/"
  cp "$SUB/$V/tests/test_account.py" "$WT/tests/test_account.py"
  cp "$SUB/TASK.md" "$WT/TASK.md"
  cp "$SUB/pointers-only.tasks.json" "$WT/pointers-only.tasks.json"
  ( cd "$WT" && git init -q && git add -A && git -c user.email=b@b -c user.name=b commit -qm pristine )
  echo "$WT"
}

for V in "${VARIANTS[@]}"; do
  WT=$(stage "$V")
  OUT="$B/results/$V"; mkdir -p "$OUT"
  RES="$OUT/results.csv"; echo "trial,accept_rc,num_turns,cost_usd,wall_s,read_cue" > "$RES"
  echo "########## $V (N=$N) ##########"
  for i in $(seq 1 "$N"); do
    rdir="$OUT/t$i"; mkdir -p "$rdir"
    git -C "$WT" reset --hard -q HEAD
    rm -f "$WT/PLAN.md"; rm -rf "$WT/.pigeon/handoffs" "$WT/.pigeon/context" "$WT/.pigeon/coordinate" "$WT/.pigeon/metrics.jsonl"
    defs=$(( $(grep -c 'def to_wire\|def from_wire' "$WT/ledger/account.py") + $(grep -c 'def to_wire\|def from_wire\|\.to_wire(' "$WT/tests/test_account.py") ))
    [ "$defs" -ne 0 ] && { echo "ABORT $V not pristine (added-defs=$defs) before t$i"; exit 3; }
    cd "$WT"; t0=$(date +%s)
    timeout -k 30 800 pigeon coordinate pointers-only.tasks.json --skip-permissions --telemetry --budget-usd 3 > "$rdir/run" 2>&1
    wall=$(( $(date +%s)-t0 ))
    PYTHONPATH="$WT" python "$SUB/accept.py" > "$rdir/accept" 2>&1; arc=$?
    man=$(ls -t "$WT"/.pigeon/coordinate/runs/*.json 2>/dev/null | head -1)
    cp "$man" "$rdir/manifest.json" 2>/dev/null
    turns=$(python -c "import json;d=json.load(open('$man'));print(sum((t.get('telemetry')or{}).get('num_turns',0) for t in d['tasks'].values()))" 2>/dev/null || echo NA)
    cost=$(python -c "import json;d=json.load(open('$man'));print(round(sum((t.get('telemetry')or{}).get('total_cost_usd',0) for t in d['tasks'].values()),4))" 2>/dev/null || echo NA)
    rc=$(grep -li "to_legacy\|legacy\|_dump\|_load" "$WT"/.pigeon/coordinate/logs/exp4b-null-{to_wire,from_wire}.log 2>/dev/null | wc -l)
    echo "$i,$arc,$turns,$cost,$wall,$rc" >> "$RES"
    echo "$V,$i,$arc,$turns,$cost,$wall,$rc" >> "$SUMMARY"
    echo "[$V t$i] accept_rc=$arc turns=$turns cost=\$$cost ${wall}s read_cue=$rc"
  done
  pass=$(awk -F, 'NR>1 && $2==0' "$RES" | wc -l)
  echo "=== $V: PASS $pass/$N  read-cue: $(awk -F, 'NR>1 && $6>0' "$RES"|wc -l)/$N ==="
done
echo "######### EXP-4b CALIBRATION DONE $(date -Is) #########"
echo "--- summary ---"; column -t -s, "$SUMMARY"
echo ""; echo "R meter (pointers-only pass rate per variant):"
for V in "${VARIANTS[@]}"; do
  p=$(awk -F, -v v="$V" 'NR>1 && $1==v && $3==0' "$SUMMARY" | wc -l)
  n=$(awk -F, -v v="$V" 'NR>1 && $1==v' "$SUMMARY" | wc -l)
  echo "  $V: $p/$n"
done
