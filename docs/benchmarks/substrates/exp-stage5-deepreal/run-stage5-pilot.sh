#!/usr/bin/env bash
# Stage 5 pilot — deep-real substrate (external ISO-4217 minor-units fact).
#
# Self-contained: builds a throwaway git repo from THIS committed substrate, runs
# N trials of one arm, grades each with the held-out accept.py (never in the repo).
# Uses the reliable `sonnet` runner (measured; no agy flakiness).
#
#   bash run-stage5-pilot.sh [N] [arm]
#     N    default 4 (pilot)
#     arm  no-code-baseline | pointers-only | with-derived   (default no-code-baseline)
#
# no-code-baseline: the repo has NO money.py and NO TASK.md file — the agent gets
#   only the task text in the tasks JSON and writes money.py from priors. This
#   measures the GUESSING FLOOR the pointers-only result must be read against.
# pointers-only / with-derived: the pristine money.py (x100 for USD/EUR only) +
#   TASK.md are present; the agent extends it for JPY/BHD.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$(cd "$HERE/../../../.." && pwd)"
N="${1:-4}"; ARM="${2:-no-code-baseline}"
TASKS="$HERE/${ARM}.tasks.json"
[ -f "$TASKS" ] || { echo "no such arm: $TASKS" >&2; exit 2; }
command -v claude >/dev/null || { echo "claude not on PATH" >&2; exit 2; }

WORK="$(mktemp -d)"; REPO="$WORK/repo"
mkdir -p "$REPO/ledger" "$REPO/tests" "$REPO/.pigeon"
: > "$REPO/ledger/__init__.py"
cp "$HERE/accept.py" "$WORK/accept.py"                 # held OUT of the agent tree
cp "$MAIN/.pigeon/config.yaml"         "$REPO/.pigeon/config.yaml"
cp "$MAIN/.pigeon/handoff.schema.json" "$REPO/.pigeon/handoff.schema.json"
cp "$TASKS" "$REPO/$ARM.tasks.json"
printf '# Agent protocol\n\nDo only the one step in your handoff, then stop. Run shell commands synchronously; never defer as background tasks. No conda env; ignore package-policy constraints.\n' > "$REPO/AGENTS.md"

NOCODE=0; [ "$ARM" = "no-code-baseline" ] && NOCODE=1
if [ "$NOCODE" -eq 0 ]; then
  cp "$HERE/ledger/money.py"     "$REPO/ledger/money.py"   # pristine x100 (USD/EUR)
  cp "$HERE/TASK.md"             "$REPO/TASK.md"
  cp "$HERE/tests/test_money.py" "$REPO/tests/test_money.py"
fi

git -C "$REPO" init -q
git -C "$REPO" add -A
git -C "$REPO" -c user.email=s5@local -c user.name=s5 commit -q -m pristine

OUT="$WORK/results"; mkdir -p "$OUT"
RES="$OUT/results.csv"; echo "trial,arm,accept_rc,turns,cost_usd,wall_s,jpy_ok,bhd_ok" > "$RES"

for i in $(seq 1 "$N"); do
  rdir="$OUT/t$i"; mkdir -p "$rdir"
  git -C "$REPO" reset --hard -q HEAD
  rm -rf "$REPO/.pigeon/handoffs" "$REPO/.pigeon/context" "$REPO/.pigeon/coordinate" "$REPO/.pigeon/metrics.jsonl"
  git -C "$REPO" clean -fdq ledger tests 2>/dev/null   # drop any agent-created files from prior trial
  [ "$NOCODE" -eq 1 ] && rm -f "$REPO/ledger/money.py"
  # pristine guard: for the code arms, money.py must not yet handle JPY/BHD
  if [ "$NOCODE" -eq 0 ]; then
    j=$(grep -c 'JPY\|BHD' "$REPO/ledger/money.py")
    [ "$j" -ne 0 ] && { echo "ABORT: money.py not pristine before t$i (JPY/BHD refs=$j)" >&2; exit 4; }
  fi

  t0=$(date +%s)
  ( cd "$REPO" && timeout -k 30 900 pigeon coordinate "$ARM.tasks.json" \
      --skip-permissions --telemetry --budget-usd 3 ) > "$rdir/run" 2>&1
  wall=$(( $(date +%s) - t0 ))
  if grep -rqi "flags provided but not defined" "$REPO/.pigeon/coordinate/logs" 2>/dev/null; then
    echo "ABORT t$i: runner rejected an unknown flag (INVALID trial)." >&2; exit 5; fi

  PYTHONPATH="$REPO" python "$WORK/accept.py" > "$rdir/accept" 2>&1; arc=$?
  man="$(ls -t "$REPO"/.pigeon/coordinate/runs/*.json 2>/dev/null | head -1)"
  cp "$man" "$rdir/manifest.json" 2>/dev/null
  mkdir -p "$rdir/.pigeon/coordinate"; cp -r "$REPO/.pigeon/coordinate/logs" "$rdir/.pigeon/coordinate/logs" 2>/dev/null
  cp "$REPO/ledger/money.py" "$rdir/money.py" 2>/dev/null
  turns=$(python - "$man" <<'PY' 2>/dev/null || echo NA
import json,sys
d=json.load(open(sys.argv[1])); print(sum((t.get("telemetry") or {}).get("num_turns",0) for t in d["tasks"].values()))
PY
)
  cost=$(python - "$man" <<'PY' 2>/dev/null || echo NA
import json,sys
d=json.load(open(sys.argv[1])); print(round(sum((t.get("telemetry") or {}).get("total_cost_usd",0) for t in d["tasks"].values()),4))
PY
)
  # per-currency correctness on the held-out boundary (from accept output)
  jpy_ok=$(grep -q "JPY" "$rdir/accept" && echo 0 || echo 1)   # 1 = JPY line NOT flagged = correct
  bhd_ok=$(grep -q "BHD" "$rdir/accept" && echo 0 || echo 1)
  echo "$i,$ARM,$arc,$turns,$cost,$wall,$jpy_ok,$bhd_ok" >> "$RES"
  echo "[t$i] accept_rc=$arc turns=$turns cost=\$$cost ${wall}s jpy_ok=$jpy_ok bhd_ok=$bhd_ok"
done

[ -n "${STAGE5_OUT:-}" ] && { mkdir -p "$STAGE5_OUT"; cp -r "$OUT/." "$STAGE5_OUT/"; echo "persisted -> $STAGE5_OUT"; }
echo "=== STAGE 5 PILOT ($ARM, N=$N) ==="
echo "PASS (accept_rc==0): $(awk -F, 'NR>1 && $3==0' "$RES" | wc -l)/$N"
echo "  (no-code PASS rate = the guessing FLOOR; pointers-only near it = trace genuinely hidden)"
cat "$RES"
