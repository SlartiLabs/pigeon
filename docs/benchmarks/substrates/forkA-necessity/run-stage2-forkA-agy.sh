#!/usr/bin/env bash
# Stage 2 (cross-model) — NECESSITY side, receiver = agy/Gemini.
#
# Self-contained: builds a throwaway git repo from THIS committed Fork-A substrate
# (pristine account.py, held-out accept.py), runs N trials of one arm, grades each.
# The off-disk contract is 0%-recoverable from the code, so:
#   pointers-only-agy  -> expected ~0/8 (necessity: no residue, no recovery)
#   with-derived-agy   -> expected ~8/8 (carried state.derived makes it implementable)
#
# CONTRACT.md is NEVER copied into the working repo — it would leak the contract
# to the null arm. The with-derived architect inlines the contract from its prompt.
#
# Roles are free (pigeon's premise; agy v1.0.16 runs shell, so it can be architect):
#   bash run-stage2-forkA-agy.sh [N] [arm] [ARCH_RUNNER] [RECV_RUNNER]
#     N     default 1 (pilot; confirm tier is N=8)
#     arm   pointers-only-agy | with-derived-agy   (default pointers-only-agy)
#   e.g.  ... 8 with-derived-agy agy agy    # all-Gemini necessity chain
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$(cd "$HERE/../../../.." && pwd)"
N="${1:-1}"; ARM="${2:-pointers-only-agy}"; ARCH_RUNNER="${3:-}"; RECV_RUNNER="${4:-}"
TASKS="$HERE/${ARM}.tasks.json"
[ -f "$TASKS" ] || { echo "no such arm: $TASKS" >&2; exit 2; }
command -v agy   >/dev/null || { echo "agy not on PATH"    >&2; exit 2; }
command -v claude>/dev/null || { echo "claude not on PATH" >&2; exit 2; }

WORK="$(mktemp -d)"; REPO="$WORK/repo"
mkdir -p "$REPO/ledger" "$REPO/tests" "$REPO/.pigeon"
cp "$HERE/ledger/account.py" "$REPO/ledger/account.py"; : > "$REPO/ledger/__init__.py"
cp "$HERE/tests/test_account.py" "$REPO/tests/test_account.py"
cp "$TASKS" "$REPO/$ARM.tasks.json"
cp "$HERE/accept.py" "$WORK/accept.py"                 # held OUT of the agent tree
# NOTE: CONTRACT.md is intentionally NOT copied — it must never enter the repo.
cp "$MAIN/.pigeon/config.yaml"         "$REPO/.pigeon/config.yaml"
cp "$MAIN/.pigeon/handoff.schema.json" "$REPO/.pigeon/handoff.schema.json"
grep -q '"derived"' "$REPO/.pigeon/handoff.schema.json" || { echo "schema not 1.2" >&2; exit 3; }

ARCH="$ARCH_RUNNER" RECV="$RECV_RUNNER" python - "$REPO/$ARM.tasks.json" <<'PY'
import json, os, sys
p=sys.argv[1]; arch=os.environ.get("ARCH") or None; recv=os.environ.get("RECV") or None
d=json.load(open(p))
for t in d["tasks"]:
    if t["id"]=="architect" and arch: t["runner"]=arch
    elif t["id"]!="architect" and recv: t["runner"]=recv
json.dump(d, open(p,"w"), indent=2)
print("runners:", ", ".join(f'{t["id"]}={t["runner"]}' for t in d["tasks"]))
PY
printf '# Agent protocol\n\nDo only the one step in your handoff, then stop. If the step is a shell command (e.g. `pigeon handoff`), run it directly and synchronously in this turn — never defer it as a background task and never wait for a notification. The workspace uses no conda env; ignore package-policy constraints.\n' > "$REPO/AGENTS.md"

git -C "$REPO" init -q
git -C "$REPO" add ledger tests AGENTS.md "$ARM.tasks.json" .pigeon/config.yaml .pigeon/handoff.schema.json
git -C "$REPO" -c user.email=s2@local -c user.name=s2 commit -q -m pristine

OUT="$WORK/results"; mkdir -p "$OUT"
RES="$OUT/results.csv"; echo "trial,arm,accept_rc,turns,cost_usd,wall_s,recv_fired,injected,used_contract" > "$RES"

for i in $(seq 1 "$N"); do
  rdir="$OUT/t$i"; mkdir -p "$rdir"
  git -C "$REPO" reset --hard -q HEAD
  rm -rf "$REPO/.pigeon/handoffs" "$REPO/.pigeon/context" "$REPO/.pigeon/coordinate" "$REPO/.pigeon/metrics.jsonl"
  defs=$(grep -c 'def to_wire\|def from_wire' "$REPO/ledger/account.py")
  [ "$defs" -ne 0 ] && { echo "ABORT: not pristine before t$i (defs=$defs)" >&2; exit 4; }

  t0=$(date +%s)
  ( cd "$REPO" && timeout -k 30 900 pigeon coordinate "$ARM.tasks.json" \
      --skip-permissions --telemetry --budget-usd 3 ) > "$rdir/run" 2>&1
  wall=$(( $(date +%s) - t0 ))

  # GUARD (data-integrity): if any runner rejected an unknown CLI flag, it printed
  # its usage and never did the work — an INVALID trial, not a failure. This is the
  # agy `--json` telemetry-flag break: agy has no --json, so telemetry_flags.agy
  # MUST stay []. Abort loudly rather than record a false 0/N.
  if grep -rqi "flags provided but not defined\|flag provided but not defined" \
       "$REPO/.pigeon/coordinate/logs" 2>/dev/null; then
    echo "ABORT t$i: a runner rejected an unknown CLI flag (usage printed, no work done)." >&2
    echo "  Almost certainly telemetry_flags.agy is not [] in .pigeon/config.yaml." >&2
    echo "  Set it back to [] and re-run. This trial is INVALID." >&2
    exit 5
  fi

  PYTHONPATH="$REPO" python "$WORK/accept.py" > "$rdir/accept" 2>&1; arc=$?
  man="$(ls -t "$REPO"/.pigeon/coordinate/runs/*.json 2>/dev/null | head -1)"
  cp "$man" "$rdir/manifest.json" 2>/dev/null
  mkdir -p "$rdir/.pigeon/coordinate"
  cp -r "$REPO/.pigeon/coordinate/logs" "$rdir/.pigeon/coordinate/logs" 2>/dev/null
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
  logdir="$REPO/.pigeon/coordinate/logs"
  recv_fired=$(find "$logdir" -name '*to_wire.log' -size +0c 2>/dev/null | head -1 | grep -c . )
  injected=$(grep -l "Carried reasoning" "$logdir"/*to_wire.log 2>/dev/null | wc -l)
  # did the produced serializer actually use the off-disk contract key 'acct'?
  used_contract=$(grep -c '"acct"' "$REPO/ledger/account.py" 2>/dev/null)
  echo "$i,$ARM,$arc,$turns,$cost,$wall,$recv_fired,$injected,$used_contract" >> "$RES"
  echo "[t$i] accept_rc=$arc turns=$turns cost=\$$cost ${wall}s recv_fired=$recv_fired injected=$injected used_contract=$used_contract"
done

if [ -n "${STAGE2_OUT:-}" ]; then mkdir -p "$STAGE2_OUT"; cp -r "$OUT/." "$STAGE2_OUT/"; echo "persisted -> $STAGE2_OUT"; fi
echo "=== STAGE 2 NECESSITY ($ARM, N=$N) ==="
echo "PASS (accept_rc==0): $(awk -F, 'NR>1 && $3==0' "$RES" | wc -l)/$N   (expected ~0/N for pointers-only, ~N/N for with-derived)"
echo "artifacts: ${STAGE2_OUT:-$OUT}"
echo "cat $RES:"
cat "$RES"
echo ""
echo "=== CANONICAL RETOKENIZATION & ESTIMATED COST FOR AGY ==="
python "$MAIN/docs/benchmarks/instruments/canonical-retokenize.py" "$OUT"/t*/manifest.json --price "$MAIN/docs/benchmarks/instruments/prices.template.json"
