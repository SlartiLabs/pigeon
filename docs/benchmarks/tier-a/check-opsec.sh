#!/usr/bin/env bash
# Pre-publication opsec guard (PROTOCOL §0/§8): fail if any private identity
# string leaks into committed docs/benchmarks/. This script contains NO names — the
# deny-list is loaded at runtime from the gitignored docs/benchmarks/tier-a/private-map.json
# (so the guard itself never bleeds the strings it guards against).
set -euo pipefail
cd "$(dirname "$0")/../.."

MAP="docs/benchmarks/tier-a/private-map.json"
if [ ! -f "$MAP" ]; then
  echo "opsec: $MAP not found (it is gitignored). Copy private-map.template.json"
  echo "       to it and fill 'deny' with every private string (repo/org/author/"
  echo "       codename) before publishing. Skipping (cannot check)."
  exit 0
fi

PATTERN="$(python3 - "$MAP" <<'PY'
import json, re, sys
data = json.load(open(sys.argv[1]))
deny = data.get("deny")
vals = set()
if isinstance(deny, list):
    vals = {re.escape(s) for s in deny if isinstance(s, str) and len(s) >= 3}
else:  # fall back to every string value in the map
    def walk(o):
        if isinstance(o, dict): [walk(v) for v in o.values()]
        elif isinstance(o, list): [walk(v) for v in o]
        elif isinstance(o, str) and len(o) >= 3: vals.add(re.escape(o))
    walk(data)
print("|".join(sorted(vals)))
PY
)"

if [ -z "$PATTERN" ]; then
  echo "opsec: deny-list empty; nothing to check (fill 'deny' in $MAP)"; exit 0
fi

HITS="$(git grep -niE "$PATTERN" -- docs/benchmarks/ 2>/dev/null || true)"
if [ -n "$HITS" ]; then
  echo "OPSEC LEAK — private identity string(s) found in committed docs/benchmarks/:"
  echo "$HITS"
  exit 1
fi
echo "opsec: docs/benchmarks/ is clean of the private identity strings in $MAP"
