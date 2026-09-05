"""Build `data/banks.json` from the sourced captures in `data/sources/`.

The captures are the source of truth, not this output. Each one records the URL
it was read from and the date it was read, and this script carries that through
to every branch so a consumer can always answer "where did this row come from,
and when was it last checked?" — the question the existing public datasets
cannot answer at all.

It also records HOW a bank was sourced, which is not the same as whether it is
correct:

  * `first_party`  — read from the bank's own website. Best evidence.
  * `bach_table`   — from the consolidated BACH routing table (26.06.2025),
                     published by Dhaka Bank PLC. Used ADDITIVELY for banks that
                     publish no routing numbers themselves. It is a snapshot, so
                     it is never authority for a branch being ABSENT.

Run: python scripts/build.py
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources"
OUT = ROOT / "data" / "banks.json"

#: Both packages ship the dataset inside themselves so they have no runtime
#: dependency on the repo layout. Those copies are written here rather than by
#: hand: a package quietly a build behind is a package that disagrees with its
#: own documentation, and nothing in either test suite would notice.
PACKAGE_COPIES = (ROOT / "packages" / "python" / "src" / "bdbanks" / "banks.json",)

#: The JS package gets a TypeScript module, not a .json file.
#:
#: `import data from "./banks.json"` type-checks, bundles and passes the whole
#: vitest suite — and then throws ERR_IMPORT_ATTRIBUTE_MISSING the moment anyone
#: imports the published package from plain Node ESM, which needs
#: `with { type: "json" }`. Emitting a module sidesteps the whole argument: it
#: works in Node ESM, in bundlers and in the browser, with no attribute and no
#: filesystem read. The payload is a single JSON string parsed at load, which
#: V8 also parses faster than an equivalent object literal.
JS_DATASET = ROOT / "packages" / "js" / "src" / "dataset.ts"

#: PyPI and npm each render the README found beside the manifest, so both
#: packages need their own copy of the one at the repo root. Written here for the
#: same reason as the dataset: a hand-copied README goes stale silently.
README = ROOT / "README.md"
README_COPIES = (
    ROOT / "packages" / "python" / "README.md",
    ROOT / "packages" / "js" / "README.md",
)

#: A package whose metadata says MIT but carries no licence text is not actually
#: licensed to the person who installed it.
LICENSE = ROOT / "LICENSE"
LICENSE_COPIES = (
    ROOT / "packages" / "python" / "LICENSE",
    ROOT / "packages" / "js" / "LICENSE",
)

#: The consolidated BACH table, published by a scheduled bank. Captures citing it
#: are corroborated rather than first-party.
BACH_HOST = "dhakabank.com.bd"

#: Districts renamed by Bangladesh but still printed under the old spelling by
#: many banks, plus Dhaka's two clearing zones which are not districts at all.
#: Normalised in the OUTPUT only — the captures keep what was actually read, so
#: provenance stays honest and the mapping stays visible here.
DISTRICT_ALIASES = {
    "BARISAL": "BARISHAL",
    "COMILLA": "CUMILLA",
    "JESSORE": "JASHORE",
    "JHALAKATI": "JHALOKATI",
    "CHITTAGONG": "CHATTOGRAM",
    "BOGRA": "BOGURA",
    "DHAKA-NORTH": "DHAKA",
    "DHAKA-SOUTH": "DHAKA",
}


def header(text: str, field: str) -> str | None:
    m = re.search(rf"^# {field}:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else None


def parse_capture(path: Path) -> dict | None:
    """One bank: `<code>_<name>.txt`, lines of ROUTING|NAME|DISTRICT."""
    if path.name.startswith("_"):
        return None
    text = path.read_text(encoding="utf-8")
    code = path.name.split("_")[0]
    source = header(text, "source")
    checked = header(text, "checked")
    name = header(text, "name")
    if not source or not checked:
        raise SystemExit(f"{path.name}: missing '# source:' or '# checked:'")
    if not name:
        raise SystemExit(f"{path.name}: missing '# name:' — a bank code without a name is unusable")

    branches = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            raise SystemExit(f"{path.name}: expected ROUTING|NAME|DISTRICT, got {line!r}")
        routing, bname, district = parts
        if not re.fullmatch(r"\d{9}", routing):
            raise SystemExit(f"{path.name}: {routing!r} is not a 9-digit routing number")
        if not routing.startswith(code):
            raise SystemExit(
                f"{path.name}: {routing} is not on this bank's own prefix {code} — "
                "the first three digits ARE the bank"
            )
        d = district.upper()
        # `NA` is not a district. The Controller General's rows have none because
        # they are ministry accounting units, not branches — so say null rather
        # than inventing a 65th district in a country that has 64.
        canon = None if d in {"NA", "N/A", "UNKNOWN", ""} else DISTRICT_ALIASES.get(d, d)
        branches.append({"routing": routing, "name": bname, "district": canon})

    if not branches:
        raise SystemExit(f"{path.name}: no branches")

    payable = (header(text, "payable") or "true").lower() != "false"
    entry = {
        "code": code,
        "name": name,
        "payable": payable,
        "branches": sorted(branches, key=lambda b: b["routing"]),
        "source": {
            "url": source,
            "checked": checked,
            "kind": "bach_table" if BACH_HOST in source else "first_party",
        },
    }
    if not payable:
        entry["payable_reason"] = header(text, "payable-reason") or "not a payable institution"
    return entry


def legal_names() -> dict[str, str]:
    """slug -> the regulator's current legal name."""
    path = SOURCES / "_bank_names.txt"
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            slug, name = line.split("|")
            out[slug.strip()] = name.strip()
    return out


def main() -> None:
    banks = [b for p in sorted(SOURCES.glob("*.txt")) if (b := parse_capture(p))]
    if not banks:
        raise SystemExit("no captures found")

    routings: dict[str, str] = {}
    for bank in banks:
        for br in bank["branches"]:
            if br["routing"] in routings:
                raise SystemExit(
                    f"{br['routing']} is claimed by two banks: "
                    f"{routings[br['routing']]} and {bank['code']}"
                )
            routings[br["routing"]] = bank["code"]

    districts = sorted(
        {b["district"] for bank in banks for b in bank["branches"] if b["district"]}
    )

    # Digits 4-5 ARE the district, so one code must resolve to exactly one
    # district. When it resolves to two, one row's district column is wrong --
    # and the column is the half that gets believed, because nothing about the
    # row looks off. Two shipped before this guard existed: a Brahmanbaria
    # branch labelled BOGURA, and a Cox's Bazar routing wearing a Dhaka branch
    # name. A district may legitimately hold several codes (Dhaka does); a code
    # holding several districts is always an error.
    by_code: dict[str, dict[str, int]] = {}
    for bank in banks:
        for br in bank["branches"]:
            if br["district"]:
                by_code.setdefault(br["routing"][3:5], {}).setdefault(br["district"], 0)
                by_code[br["routing"][3:5]][br["district"]] += 1
    if ambiguous := {c: d for c, d in by_code.items() if len(d) > 1}:
        raise SystemExit(
            "a district code resolves to more than one district — the minority "
            f"rows are mislabelled: {ambiguous}"
        )
    if len(districts) > 64:
        raise SystemExit(
            f"{len(districts)} districts, but Bangladesh has 64 — an alias is missing: {districts}"
        )
    payload = {
        "generated": date.today().isoformat(),
        "counts": {
            "banks": len(banks),
            "payable_banks": sum(1 for b in banks if b["payable"]),
            "branches": sum(len(b["branches"]) for b in banks),
            "districts": len(districts),
        },
        "districts": districts,
        "banks": sorted(banks, key=lambda b: b["code"]),
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    OUT.write_text(rendered, encoding="utf-8")
    # Minified in the packages: every install pays for that whitespace, and
    # nobody reads the copy inside node_modules. `data/banks.json` stays indented
    # because it is the file people review in diffs.
    packed = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    for copy in PACKAGE_COPIES:
        copy.write_text(packed, encoding="utf-8")

    JS_DATASET.write_text(
        "// Generated by scripts/build.py — do not edit.\n"
        "// A JSON *module* rather than a .json import, so the published package\n"
        "// works under plain Node ESM without an import attribute.\n"
        "const raw =\n  "
        + json.dumps(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        + ";\n\nexport default JSON.parse(raw);\n",
        encoding="utf-8",
    )

    readme = README.read_text(encoding="utf-8")
    for copy in README_COPIES:
        copy.write_text(readme, encoding="utf-8")

    licence = LICENSE.read_text(encoding="utf-8")
    for copy in LICENSE_COPIES:
        copy.write_text(licence, encoding="utf-8")

    first = sum(1 for b in banks if b["source"]["kind"] == "first_party")
    unpayable = [b for b in banks if not b["payable"]]
    print(f"  wrote {OUT.relative_to(ROOT)}")
    for copy in (*PACKAGE_COPIES, JS_DATASET, *README_COPIES, *LICENSE_COPIES):
        print(f"        + {copy.relative_to(ROOT)}")
    print(f"    banks     {payload['counts']['banks']}  ({len(unpayable)} flagged not payable)")
    print(f"    branches  {payload['counts']['branches']}")
    print(f"    districts {payload['counts']['districts']}")
    print(f"    sourced   {first} from the bank's own site, {len(banks) - first} from the BACH table")


if __name__ == "__main__":
    main()
