#!/usr/bin/env bash
# Fast checks, no cost: manifests, skills, the file-cleanup tests, and that
# the Proton connector bundle starts and lists its tools.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ marketplace"
claude plugin validate . >/dev/null && echo "  ok"

for p in plugins/*/; do
  name=$(basename "$p")
  claude plugin validate "$p.claude-plugin/plugin.json" >/dev/null && echo "  $name ok"
  for d in "$p"skills/*/; do
    [ -f "${d}SKILL.md" ] || { echo "  missing SKILL.md in $d"; exit 1; }
  done
done

echo "→ file-cleanup and claude-files tests"
python3 -m unittest discover -s plugins/life-admin/skills/file-cleanup/scripts -q
python3 -m unittest discover -s plugins/life-admin/skills/claude-files/scripts -p "test_*.py" -q

echo "→ proton-mail connector"
reply=$( (printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'; sleep 2) \
  | node plugins/proton-mail/server/server.mjs 2>/dev/null)
count=$(printf '%s' "$reply" | grep -o '"name":"[a-z_]*"' | grep -vc proton-mail || true)
[ "$count" -ge 10 ] && echo "  $count tools" || { echo "  connector failed to list tools"; exit 1; }

echo "All checks passed."
