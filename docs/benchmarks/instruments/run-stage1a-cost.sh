#!/usr/bin/env bash
# Stage 1a — cost single-shot -> powered estimate. Reruns Experiment 1's
# cookiecutter `shoutcase` task, naive (single claude call) vs pigeon (coordinate),
# at N per arm, measuring USD cost per arm from telemetry. The point is a CI on the
# "token-neutral to mildly negative" cost claim, not a hypothesis test.
#
#   bash run-stage1a-cost.sh <CC_CLONE> [N]
#     CC_CLONE  path to a cookiecutter clone at the Exp-1 base SHA
#     N         trials per arm (default 8)
#
# Both arms get the SAME task. Success is a structural check (the filter is defined
# in extensions.py AND registered in environment.py's default_extensions); cost is
# the comparable metric (est_cost_usd, measured for both via --output-format json).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$(cd "$HERE/../../.." && pwd)"
SRC="${1:?usage: run-stage1a-cost.sh CC_CLONE [N]}"; N="${2:-8}"
BASE_SHA="c88fbe921c97c58b65f1883ba90a0ab53cc91b34"
command -v claude >/dev/null || { echo "claude not on PATH" >&2; exit 2; }
[ -d "$SRC/.git" ] || { echo "not a git clone: $SRC" >&2; exit 2; }

TASK='Add a built-in `shoutcase` Jinja2 filter to cookiecutter, available BY DEFAULT (usable in a template as {{ "hi"|shoutcase }} with NO _extensions key). Define a ShoutcaseExtension class in cookiecutter/extensions.py that registers environment.filters["shoutcase"] to a function returning the input string uppercased, and register that extension in the default_extensions list in cookiecutter/environment.py. Keep the existing test suite green. Do not add a _extensions entry anywhere.'

WORK="$(mktemp -d)"; OUT="$WORK/results"; mkdir -p "$OUT"
RES="$OUT/results.csv"; echo "arm,trial,success,cost_usd,turns,wall_s" > "$RES"

# One clean checkout we reset between trials (both arms share it, reset each time).
REPO="$WORK/repo"; cp -r "$SRC" "$REPO"
git -C "$REPO" reset --hard -q "$BASE_SHA"; git -C "$REPO" clean -fdq

structural_ok () {  # 1 if the filter is defined AND registered by default
  local ext="$REPO/cookiecutter/extensions.py" env="$REPO/cookiecutter/environment.py"
  grep -qi "shoutcase" "$ext" 2>/dev/null && \
  grep -qi "filters\['shoutcase'\]\|filters\[\"shoutcase\"\]\|shoutcase" "$ext" 2>/dev/null && \
  grep -qi "Shoutcase" "$env" 2>/dev/null && echo 1 || echo 0
}

run_naive () {  # single claude call, edits the repo directly
  local rdir="$1"
  ( cd "$REPO" && timeout -k 30 600 claude -p "$TASK" --model sonnet \
      --dangerously-skip-permissions --output-format json ) > "$rdir/out.json" 2>"$rdir/err"
  python3 - "$rdir/out.json" <<'PY' 2>/dev/null || echo "NA NA"
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: print("NA NA"); sys.exit()
print(d.get("total_cost_usd","NA"), d.get("num_turns","NA"))
PY
}

run_pigeon () {  # coordinate: architect scopes, implementer edits
  local rdir="$1"
  mkdir -p "$REPO/.pigeon"
  cp "$MAIN/.pigeon/config.yaml" "$REPO/.pigeon/config.yaml"
  cp "$MAIN/.pigeon/handoff.schema.json" "$REPO/.pigeon/handoff.schema.json"
  cat > "$REPO/s1a.tasks.json" <<JSON
{"sid":"s1a","tasks":[
 {"id":"architect","runner":"sonnet","doing":"You are the architect. Scope this task, then hand off a brief pointer to the implementer (do NOT edit files): $TASK","pack":false},
 {"id":"impl","runner":"sonnet","needs":["architect"],"receives":["repo://cookiecutter/extensions.py","repo://cookiecutter/environment.py"],"doing":"Implement exactly this, editing only cookiecutter/extensions.py and cookiecutter/environment.py: $TASK Do not run tests; just edit, then record your handoff.","pack":false}
]}
JSON
  ( cd "$REPO" && timeout -k 30 900 pigeon coordinate s1a.tasks.json \
      --skip-permissions --telemetry --budget-usd 3 ) > "$rdir/run" 2>&1
  local man; man="$(ls -t "$REPO"/.pigeon/coordinate/runs/*.json 2>/dev/null | head -1)"
  python3 - "$man" <<'PY' 2>/dev/null || echo "NA NA"
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: print("NA NA"); sys.exit()
c=sum((t.get("telemetry") or {}).get("total_cost_usd",0) for t in d["tasks"].values())
tn=sum((t.get("telemetry") or {}).get("num_turns",0) for t in d["tasks"].values())
print(round(c,4), tn)
PY
}

for arm in naive pigeon; do
  for i in $(seq 1 "$N"); do
    rdir="$OUT/$arm-$i"; mkdir -p "$rdir"
    git -C "$REPO" reset --hard -q "$BASE_SHA"; git -C "$REPO" clean -fdq
    rm -rf "$REPO/.pigeon/handoffs" "$REPO/.pigeon/coordinate" "$REPO/.pigeon/metrics.jsonl" "$REPO/s1a.tasks.json"
    t0=$(date +%s)
    if [ "$arm" = naive ]; then read -r cost turns < <(run_naive "$rdir"); else read -r cost turns < <(run_pigeon "$rdir"); fi
    wall=$(( $(date +%s) - t0 )); ok=$(structural_ok)
    echo "$arm,$i,$ok,$cost,$turns,$wall" >> "$RES"
    echo "[$arm t$i] success=$ok cost=\$$cost turns=$turns ${wall}s"
  done
done

[ -n "${STAGE1A_OUT:-}" ] && { mkdir -p "$STAGE1A_OUT"; cp -r "$OUT/." "$STAGE1A_OUT/"; echo "persisted -> $STAGE1A_OUT"; }
echo "=== STAGE 1a (N=$N/arm) ==="
for arm in naive pigeon; do
  awk -F, -v a="$arm" 'NR>1 && $1==a && $4!="NA"{s+=$4;n++;ok+=$3} END{if(n)printf "%s: mean_cost=$%.4f  n=%d  success=%d/%d\n",a,s/n,n,ok,n}' "$RES"
done
cat "$RES"
