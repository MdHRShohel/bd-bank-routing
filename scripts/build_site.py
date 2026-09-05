"""Build the static site's data files from `data/banks.json`.

The site is plain HTML/CSS/JS with no build step of its own; this script exists
only to reshape the canonical dataset into something a browser should be asked
to download.

`data/banks.json` is 1.4 MB, and shipping it whole to answer one nine-digit
lookup is the kind of thing this project exists to argue against. Two files
instead:

* `meta.json`   — banks, provenance, counts, and the district code map. Small
                  enough to render the whole page from, and fetched first.
* `branches.txt` — one `routing|name` line per branch, fetched in the
                  background while the reader is still reading.

`branches.txt` carries no district, because it does not need to: digits 4-5 of
every routing ARE the district, verified across all 11,426 rows at build time.
The site resolves districts through `districtByCode`, which makes the page a
demonstration of the claim it opens with rather than a restatement of it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seo import slugify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "banks.json"
OUT = ROOT / "site" / "data"


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))

    # Digits 4-5 -> district. build.py already refuses to emit a code that
    # resolves to two districts, so this is a total function over the dataset.
    district_by_code: dict[str, str] = {}
    for bank in payload["banks"]:
        for br in bank["branches"]:
            if br["district"]:
                district_by_code.setdefault(br["routing"][3:5], br["district"])

    # …but only if it really is total. A single row whose stored district
    # disagrees with its own code would make every district on the site a guess,
    # so prove it here rather than trusting the upstream guard.
    for bank in payload["banks"]:
        for br in bank["branches"]:
            code = br["routing"][3:5]
            if br["district"] and district_by_code[code] != br["district"]:
                raise SystemExit(
                    f"{br['routing']} is filed under {br['district']} but its own "
                    f"digits say {district_by_code[code]} — the site cannot derive "
                    "districts until this is settled"
                )

    meta = {
        "generated": payload["generated"],
        "counts": payload["counts"],
        "districts": payload["districts"],
        "districtByCode": dict(sorted(district_by_code.items())),
        "banks": [
            {
                "code": b["code"],
                "name": b["name"],
                "slug": slugify(b["name"]),
                "payable": b["payable"],
                "payableReason": b.get("payable_reason"),
                "source": b["source"],
                "branchCount": len(b["branches"]),
                "districtCount": len({br["district"] for br in b["branches"] if br["district"]}),
            }
            for b in payload["banks"]
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )

    lines = [
        f"{br['routing']}|{br['name']}"
        for bank in payload["banks"]
        for br in bank["branches"]
    ]
    # A name containing the delimiter would silently truncate on the client.
    if offenders := [ln for ln in lines if ln.count("|") != 1]:
        raise SystemExit(f"branch name contains the delimiter: {offenders[:3]}")
    (OUT / "branches.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    meta_kb = (OUT / "meta.json").stat().st_size / 1024
    branch_kb = (OUT / "branches.txt").stat().st_size / 1024
    print(f"  wrote {(OUT / 'meta.json').relative_to(ROOT)}     {meta_kb:6.1f} KB")
    print(f"        {(OUT / 'branches.txt').relative_to(ROOT)}  {branch_kb:6.1f} KB  ({len(lines)} branches)")


if __name__ == "__main__":
    main()
