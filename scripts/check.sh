#!/usr/bin/env bash
# Every gate this project has, in one command. Run it before any commit.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== dataset =="
python3 scripts/build.py
python3 scripts/build_site.py
python3 scripts/build_pages.py
python3 scripts/build_og.py

echo
echo "== the working tree must match what the build produces =="
# A hand-edited banks.json, or a capture edited without rebuilding, would
# otherwise ship a dataset no source file accounts for.
if ! git diff --quiet -- data/banks.json packages site 2>/dev/null; then
  echo "  generated files changed — review and commit them"
fi

echo
echo "== generated pages =="
python3 - <<'EOF'
import json, re, sys
from pathlib import Path

# A JSON-LD block that does not parse is invisible to a crawler, and nothing
# anywhere reports it. Parse every one on every build.
bad = 0
pages = [Path("site/index.html"), *sorted(Path("site/banks").glob("*/index.html"))]
for page in pages:
    text = page.read_text()
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
        try:
            json.loads(block)
        except Exception as exc:  # noqa: BLE001
            bad += 1
            print(f"  invalid JSON-LD in {page}: {exc}")
    for required in ('<link rel="canonical"', '<meta name="description"', "<h1"):
        if required not in text:
            bad += 1
            print(f"  {page} is missing {required}")
print(f"  {len(pages)} pages checked")
sys.exit(1 if bad else 0)
EOF

echo
echo "== python =="
(cd packages/python && uv run pytest -q)

echo
echo "== javascript =="
(cd packages/js && npm run --silent build && npx --no-install vitest run --reporter dot)

echo
echo "== packages as installed =="
./scripts/verify_dist.sh

echo
echo "all gates passed"
