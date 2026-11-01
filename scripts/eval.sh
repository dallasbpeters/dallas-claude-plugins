#!/usr/bin/env bash
# Runs each plugin's eval suite (costs a little: each case is a real Claude run).
#   scripts/eval.sh               all plugins, 2 runs per case
#   scripts/eval.sh life-admin    one plugin
#   RUNS=3 scripts/eval.sh        more runs
set -euo pipefail
cd "$(dirname "$0")/.."
RUNS=${RUNS:-2}
plugins=${1:-$(ls plugins)}
status=0
for p in $plugins; do
  [ -d "plugins/$p/evals" ] || continue
  echo "→ $p"
  (cd "plugins/$p" && claude plugin eval . --runs "$RUNS" --ablation none \
    --no-publish --trust-plugin -j 4 --max-cost-usd 5) || status=1
done
exit $status
