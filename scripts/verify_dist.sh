#!/usr/bin/env bash
# Build both packages and use them the way someone who installed them would.
#
# This exists because the JS package once passed every one of its 29 tests and
# was still broken on install: `import data from "./banks.json"` is fine under
# vitest and under any bundler, and throws ERR_IMPORT_ATTRIBUTE_MISSING under
# plain Node ESM. A test suite that runs against the source tree cannot see that.
# Only installing the artifact can.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "  building python..."
(cd packages/python && rm -rf dist && uv build >/dev/null 2>&1)

echo "  installing the wheel into a clean venv..."
python3 -m venv "$TMP/venv" >/dev/null
"$TMP/venv/bin/pip" install -q "$ROOT"/packages/python/dist/*.whl
"$TMP/venv/bin/python" - <<'PY'
import pathlib
import bdbanks

branch = bdbanks.lookup("225150135")
assert branch is not None and branch.bank_name == "CITY BANK PLC", branch
assert not bdbanks.check("225150135", bank_name="Citibank N.A").ok
assert len(bdbanks.banks()) == 63, len(bdbanks.banks())
assert len(bdbanks.districts()) == 64, len(bdbanks.districts())
# The "Typing :: Typed" classifier is a lie without this file: type checkers
# ignore every annotation in a package that does not ship the marker.
assert (pathlib.Path(bdbanks.__file__).parent / "py.typed").exists(), "py.typed missing from the wheel"
print("    python wheel ok")
PY

echo "  building javascript..."
(cd packages/js && npm run --silent build >/dev/null 2>&1 && rm -f ./*.tgz && npm pack --silent >/dev/null 2>&1)
TGZ="$(ls -t "$ROOT"/packages/js/bd-bank-routing-*.tgz | head -1)"

echo "  installing the tarball into a clean project..."
mkdir -p "$TMP/npm" && cd "$TMP/npm"
npm init -y >/dev/null 2>&1
npm install --silent "$TGZ" >/dev/null 2>&1
node --input-type=module -e '
import { lookup, check, banks, districts, isSettlementEndpoint } from "bd-bank-routing";
const b = lookup("225150135");
if (!b || b.bankName !== "CITY BANK PLC") throw new Error("lookup wrong: " + JSON.stringify(b));
if (check("225150135", "Citibank N.A").ok) throw new Error("name disagreement not caught");
if (banks().length !== 63) throw new Error("banks: " + banks().length);
if (districts().length !== 64) throw new Error("districts: " + districts().length);
if (!isSettlementEndpoint("TRUNCATION POINT")) throw new Error("settlement endpoint missed");
if (isSettlementEndpoint("HEAD OFFICE")) throw new Error("HEAD OFFICE must not be treated as one");
console.log("    npm tarball ok (plain Node ESM)");
'
cd "$ROOT"
rm -f packages/js/bd-bank-routing-*.tgz
echo "  both packages work as installed"
