#!/usr/bin/env bash
# Stage 3 — scale as a confound for retrieval. Generates a synthetic repo that
# buries the Exp-5 convention among N files (scale-generator.py), then runs the
# pointers-only-pack arm: the implementer relies on `pack:true` retrieval to
# surface ledger/account.py's legacy boundary among the decoys. Recovery holding
# = retrieval still ranks the trace in; recovery dropping = the scale confound bites.
#
#   bash run-stage3-scale.sh <FILES> [N] [SEED]
#     FILES  total .py count (10/50/200/1000/5000...)
#     N      trials at this scale (default 4 — screen tier)
#     SEED   generator seed (default 1)
# Held-out grader accept.py lives OUTSIDE the retrievable tree (generator guarantees).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$(cd "$HERE/../../.." && pwd)"
FILES="${1:?usage: run-stage3-scale.sh FILES [N] [SEED]}"; N="${2:-4}"; SEED="${3:-1}"
command -v claude >/dev/null || { echo "claude not on PATH" >&2; exit 2; }
command -v rg >/dev/null || echo "warning: ripgrep (rg) not found — pack retrieval may be degraded" >&2

WORK="$(mktemp -d)"; GEN="$WORK/gen"
python3 "$HERE/scale-generator.py" --out "$GEN" --files "$FILES" --seed "$SEED" >"$WORK/gen.log" 2>&1 \
  || { echo "generator failed:"; tail -5 "$WORK/gen.log"; exit 3; }
REPO="$GEN/repo"
TASKSFILE="$GEN/pointers-only-pack.tasks.json"   # generator writes it beside repo/
# pigeon needs a config (sonnet runner + retrieval globs) + 1.2 schema + git.
mkdir -p "$REPO/.pigeon"
cp "$MAIN/.pigeon/config.yaml"         "$REPO/.pigeon/config.yaml"
cp "$MAIN/.pigeon/handoff.schema.json" "$REPO/.pigeon/handoff.schema.json"
printf '# Agent protocol\n\nDo only the one step in your handoff, then stop. Run shell commands synchronously. Use the packed context bundle to find the existing partner serialization boundary. No conda env; ignore package-policy constraints.\n' > "$REPO/AGENTS.md"
git -C "$REPO" init -q; git -C "$REPO" add -A
git -C "$REPO" -c user.email=s3@local -c user.name=s3 commit -q -m pristine

OUT="$WORK/results"; mkdir -p "$OUT"
RES="$OUT/results.csv"; echo "scale,trial,accept_rc,turns,cost_usd,wall_s,packed_account" > "$RES"

for i in $(seq 1 "$N"); do
  rdir="$OUT/t$i"; mkdir -p "$rdir"
  git -C "$REPO" reset --hard -q HEAD
  rm -rf "$REPO/.pigeon/handoffs" "$REPO/.pigeon/context" "$REPO/.pigeon/coordinate" "$REPO/.pigeon/metrics.jsonl" "$REPO/.pigeon/pack"
  # pristine guard: to_wire/from_wire not yet added
  d=$(grep -c 'def to_wire\|def from_wire' "$REPO/ledger/account.py")
  [ "$d" -ne 0 ] && { echo "ABORT: not pristine before t$i" >&2; exit 4; }

  t0=$(date +%s)
  ( cd "$REPO" && timeout -k 30 900 pigeon coordinate "$TASKSFILE" \
      --skip-permissions --telemetry --budget-usd 3 ) > "$rdir/run" 2>&1
  wall=$(( $(date +%s) - t0 ))
  if grep -rqi "flags provided but not defined" "$REPO/.pigeon/coordinate/logs" 2>/dev/null; then
    echo "ABORT t$i: runner rejected an unknown flag (INVALID)." >&2; exit 5; fi

  PYTHONPATH="$REPO" python "$GEN/accept.py" > "$rdir/accept" 2>&1; arc=$?
  man="$(ls -t "$REPO"/.pigeon/coordinate/runs/*.json 2>/dev/null | head -1)"
  cp "$man" "$rdir/manifest.json" 2>/dev/null
  mkdir -p "$rdir/.pigeon/coordinate"; cp -r "$REPO/.pigeon/coordinate/logs" "$rdir/.pigeon/coordinate/logs" 2>/dev/null
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
  # retrieval signal: did the pack bundle actually include ledger/account.py?
  packed=$(grep -rl "ledger/account.py" "$REPO/.pigeon/coordinate/logs" 2>/dev/null | head -1 | grep -c .)
  echo "$FILES,$i,$arc,$turns,$cost,$wall,$packed" >> "$RES"
  echo "[scale=$FILES t$i] accept_rc=$arc turns=$turns cost=\$$cost ${wall}s packed_account=$packed"
done

[ -n "${STAGE3_OUT:-}" ] && { mkdir -p "$STAGE3_OUT"; cp -r "$OUT/." "$STAGE3_OUT/"; echo "persisted -> $STAGE3_OUT"; }
echo "=== STAGE 3 (scale=$FILES, N=$N) ==="
echo "recovery PASS: $(awk -F, 'NR>1 && $3==0' "$RES"|wc -l)/$N   pack-surfaced-account: $(awk -F, 'NR>1 && $7>0' "$RES"|wc -l)/$N"
cat "$RES"
