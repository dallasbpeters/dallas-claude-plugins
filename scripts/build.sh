#!/usr/bin/env bash
# Rebuilds the Proton connector bundle from source and packages every plugin
# as a .plugin file in dist/ (for installing without the marketplace).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ bundling proton-mail connector"
(cd plugins/proton-mail/src && npm ci --silent && npx -y esbuild@0.25.0 server.mjs \
  --bundle --platform=node --format=esm --target=node20 \
  --outfile=../server/server.mjs --log-level=warning \
  --banner:js="import { createRequire } from 'module'; const require = createRequire(import.meta.url);")
rm -rf plugins/proton-mail/src/node_modules

mkdir -p dist
for p in plugins/*/; do
  name=$(basename "$p")
  (cd "$p" && zip -qr "../../dist/$name.plugin" . -x "evals/results/*" "src/*" "*.DS_Store" "*__pycache__*")
  echo "→ dist/$name.plugin"
done
