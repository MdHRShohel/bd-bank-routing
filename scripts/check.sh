#!/usr/bin/env bash
# Every gate this project has, in one command. Run it before any commit.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== dataset =="
python3 scripts/build.py
python3 scripts/build_site.py

echo
echo "== the working tree must match what the build produces =="
# A hand-edited banks.json, or a capture edited without rebuilding, would
# otherwise ship a dataset no source file accounts for.
if ! git diff --quiet -- data/banks.json packages site/data 2>/dev/null; then
  echo "  generated files changed — review and commit them"
fi

echo
echo "== python =="
(cd packages/python && uv run pytest -q)

echo
echo "== javascript =="
(cd packages/js && npm run --silent build && npx --no-install vitest run --reporter dot)

echo
echo "all gates passed"
