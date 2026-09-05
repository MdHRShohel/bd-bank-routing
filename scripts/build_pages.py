"""Generate the crawlable pages: one per bank, plus sitemap, robots and llms.txt.

Why these exist at all: the lookup tool is a single page behind a `#/r/...`
hash, and a hash is not a URL a search engine will index. Nobody searches
"bd-bank-routing" — they search "sonali bank routing number". That query needs a
real page with that heading and those rows already in the HTML, so this writes
63 of them, each linking back into the interactive tool.

Everything here is derived from `data/banks.json`. No page is hand-edited; if a
bank's rows change, its page changes on the next build.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seo import (  # noqa: E402
    AUTHOR_GITHUB,
    AUTHOR_NAME,
    AUTHOR_SITE,
    REPO_URL,
    SITE_NAME,
    SITE_URL,
    esc,
    slugify,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "banks.json"
SITE = ROOT / "site"

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap\">"
)

FAVICON = (
    '<link rel="icon" href="{root}favicon.ico" sizes="any">'
    '<link rel="icon" type="image/svg+xml" href="'
    "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%230f172a'/><circle cx='16' cy='16' r='6' fill='%2322c55e'/></svg>"
    '">'
)

THEME_SCRIPT = """<script>
  try {
    var saved = localStorage.getItem("bdbr-theme");
    if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
  } catch (e) {}
</script>"""

GH_ICON = (
    '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0a8 8 0 0 0-2.53 '
    "15.59c.4.07.55-.17.55-.38l-.01-1.49c-2.01.37-2.53-.5-2.69-.96-.09-.23-.48-.95-.82-1.14-.28-.15-.68-.52-.01-.53."
    "63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59."
    "82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.4 7.4 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92."
    '08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48l-.01 2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z"/></svg>'
)


def head(*, title: str, description: str, canonical: str, extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(AUTHOR_NAME)}">
<meta name="color-scheme" content="dark light">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{esc(SITE_URL)}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(SITE_URL)}/og.png">
{FAVICON.replace("{root}", "../../")}
{FONTS}
<link rel="stylesheet" href="{{css}}">
{THEME_SCRIPT}
{extra}
</head>"""


def chrome_header(prefix: str) -> str:
    return f"""<header class="site-head">
  <div class="wrap">
    <a class="wordmark plain" href="{prefix}"><span class="dot" aria-hidden="true"></span>bd-bank-routing</a>
    <nav class="site-nav" aria-label="Sections">
      <a href="{prefix}#lookup">Lookup</a>
      <a href="{prefix}#banks">Banks</a>
      <a href="{prefix}#faq" class="hide-xs">FAQ</a>
      <button type="button" class="theme" id="theme-toggle" aria-label="Switch theme">
        <svg class="moon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M17.3 12.9A7.5 7.5 0 0 1 7.1 2.7a7.5 7.5 0 1 0 10.2 10.2Z"/></svg>
        <svg class="sun" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10 3.5a1 1 0 0 1-1-1V1.5a1 1 0 1 1 2 0v1a1 1 0 0 1-1 1Zm0 13a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1ZM3.5 10a1 1 0 0 1-1 1h-1a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1Zm15 0a1 1 0 0 1-1 1h-1a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1ZM5.05 5.05a1 1 0 0 1-1.41 0l-.71-.71a1 1 0 0 1 1.41-1.41l.71.7a1 1 0 0 1 0 1.42Zm11.02 11.02a1 1 0 0 1-1.42 0l-.7-.71a1 1 0 0 1 1.41-1.41l.71.7a1 1 0 0 1 0 1.42ZM5.05 14.95a1 1 0 0 1 0 1.42l-.71.7a1 1 0 0 1-1.41-1.41l.7-.71a1 1 0 0 1 1.42 0Zm11.02-11.02a1 1 0 0 1 0 1.41l-.71.71a1 1 0 1 1-1.41-1.41l.7-.71a1 1 0 0 1 1.42 0ZM10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/></svg>
      </button>
      <a class="gh" href="{esc(REPO_URL)}" aria-label="Source on GitHub">{GH_ICON}</a>
    </nav>
  </div>
</header>"""


def chrome_footer(prefix: str) -> str:
    """One footer everywhere, and the byline is the point of it.

    The author's site and repo sit together in the markup and in the Person
    JSON-LD `sameAs`, which is how a search engine learns the two identities are
    one person rather than two unrelated links.
    """
    return f"""<footer class="site-foot">
  <div class="wrap">
    <div class="byline">
      <p class="built">Built and maintained by <a href="{esc(AUTHOR_SITE)}" rel="me author">{esc(AUTHOR_NAME)}</a></p>
      <p class="links">
        <a href="{esc(AUTHOR_SITE)}" rel="me author">shohel.bro.bd</a>
        <span aria-hidden="true">·</span>
        <a href="{esc(AUTHOR_GITHUB)}" rel="me">github.com/MdHRShohel</a>
        <span aria-hidden="true">·</span>
        <a href="{esc(REPO_URL)}">source &amp; issues</a>
      </p>
    </div>
    <p class="licence">Code MIT · data CC0. Routing numbers are public facts; the point is that you can use them without asking.</p>
  </div>
</footer>"""


def bank_page(bank: dict, district_by_code: dict[str, str], generated: str) -> str:
    name = bank["name"]
    code = bank["code"]
    slug = slugify(name)
    canonical = f"{SITE_URL}/banks/{slug}/"
    branches = bank["branches"]
    districts = sorted({b["district"] for b in branches if b["district"]})
    payable = bank["payable"]

    title = f"{name} routing numbers — all {len(branches):,} branches | bd-bank-routing"
    description = (
        f"Every {name} branch routing number ({len(branches):,} branches across "
        f"{len(districts)} districts), with the district each nine-digit code points at. "
        f"Read from {bank['source']['url']} on {bank['source']['checked']}."
    )

    rows = "\n".join(
        f'<tr><td class="num">{esc(b["routing"])}</td><td>{esc(b["name"])}</td>'
        f'<td class="num">{esc(b["district"] or "—")}</td></tr>'
        for b in branches
    )

    dataset_ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{name} branch routing numbers (Bangladesh, BEFTN)",
        "description": description,
        "url": canonical,
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "isAccessibleForFree": True,
        "keywords": [
            f"{name} routing number",
            f"{name} branch code",
            "bangladesh bank routing number",
            "BEFTN routing number",
            "bank branch routing number bangladesh",
        ],
        "spatialCoverage": {"@type": "Place", "name": "Bangladesh"},
        "creator": {"@type": "Person", "name": AUTHOR_NAME, "url": AUTHOR_SITE},
        "dateModified": generated,
        "isPartOf": {"@type": "Dataset", "name": SITE_NAME, "url": f"{SITE_URL}/"},
        "distribution": {
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": f"{REPO_URL}/blob/main/data/banks.json",
        },
    }
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Bangladesh bank routing numbers", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": f"{name} routing numbers", "item": canonical},
        ],
    }

    unpayable_note = (
        ""
        if payable
        else f"""<div class="note note--warn">
      <strong>No salary can be paid to these.</strong> {esc(bank.get("payable_reason", ""))}
      They are listed so that a lookup on one of these routing numbers answers, and so a
      payroll system can refuse to <em>offer</em> them.
    </div>"""
    )

    example = branches[0]["routing"]

    return f"""{head(title=title, description=description, canonical=canonical,
        extra=f'<script type="application/ld+json">{json.dumps(dataset_ld, ensure_ascii=False)}</script>'
              f'<script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>'
        ).replace("{css}", "../../styles.css")}
<body>
<a class="skip" href="#main">Skip to content</a>
{chrome_header("../../")}

<main id="main">
<div class="hero hero--sub">
  <div class="wrap">
    <p class="eyebrow"><a href="../../">Bangladesh routing numbers</a> · {esc(code)}</p>
    <h1>{esc(name)} routing numbers</h1>
    <p class="deck">
      All {len(branches):,} {esc(name)} branches carried here, across {len(districts)} districts,
      with the nine-digit BEFTN routing number for each. Every {esc(name)} routing number begins
      <strong class="mono">{esc(code)}</strong> — the first three digits of a Bangladeshi routing
      number are the bank itself.
    </p>
    <dl class="stats">
      <div><dt>Bank code</dt><dd class="num">{esc(code)}</dd></div>
      <div><dt>Branches</dt><dd class="num">{len(branches):,}</dd></div>
      <div><dt>Districts</dt><dd class="num">{len(districts)}</dd></div>
      <div><dt>Checked</dt><dd class="num">{esc(bank["source"]["checked"])}</dd></div>
    </dl>
  </div>
</div>

<section>
  <div class="wrap">
    <header>
      <p class="eyebrow">Look one up</p>
      <h2>Check a {esc(name)} routing number</h2>
      <p>
        Paste any nine-digit routing number into the tool and it comes apart into bank,
        district, branch and check digit — and it will tell you if the bank name stored
        beside it names a different institution.
      </p>
    </header>
    <p><a class="cta" href="../../#/r/{esc(example)}">Open the lookup tool →</a></p>
    {unpayable_note}
  </div>
</section>

<section>
  <div class="wrap">
    <header>
      <p class="eyebrow">All branches</p>
      <h2>{esc(name)} branch list with routing numbers</h2>
      <p>Sorted by routing number, which groups them by district — digits 4–5 are the district code.</p>
    </header>

    <div class="table-tools">
      <div class="field">
        <label for="branch-filter">Filter branches</label>
        <input id="branch-filter" type="search" spellcheck="false" placeholder="branch name, district or routing number">
      </div>
      <p class="count-note" id="branch-count" role="status" aria-live="polite">{len(branches):,} branches</p>
    </div>

    <div class="table-scroll">
      <table id="branch-table">
        <caption>{esc(name)} — routing number, branch and district. Read from
          <a href="{esc(bank["source"]["url"])}" rel="noreferrer noopener">{esc(bank["source"]["url"])}</a>
          on {esc(bank["source"]["checked"])}.</caption>
        <thead><tr><th scope="col">Routing number</th><th scope="col">Branch</th><th scope="col">District</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </div>

    <p class="note">
      <strong>Source.</strong> {"Read from the bank's own website" if bank["source"]["kind"] == "first_party"
        else "Taken from the consolidated BACH routing table published by Dhaka Bank PLC, because this bank does not publish routing numbers itself"}
      on {esc(bank["source"]["checked"])}. Banks open, close and rename branches — this is a snapshot,
      and the date is shown so you can judge it for yourself.
    </p>
  </div>
</section>

<section>
  <div class="wrap">
    <header>
      <p class="eyebrow">Other banks</p>
      <h2>Routing numbers for every other Bangladeshi bank</h2>
    </header>
    <ul class="bank-links">{{siblings}}</ul>
  </div>
</section>
</main>

{chrome_footer("../../")}
<script>
  // Progressive enhancement only: the full table is in the HTML above, so it
  // works — and indexes — with this script blocked entirely.
  (function () {{
    var input = document.getElementById("branch-filter");
    var rows = [].slice.call(document.querySelectorAll("#branch-table tbody tr"));
    var count = document.getElementById("branch-count");
    var timer;
    input.addEventListener("input", function () {{
      clearTimeout(timer);
      timer = setTimeout(function () {{
        var q = input.value.trim().toUpperCase();
        var shown = 0;
        rows.forEach(function (tr) {{
          var hit = !q || tr.textContent.toUpperCase().indexOf(q) !== -1;
          tr.hidden = !hit;
          if (hit) shown++;
        }});
        count.textContent = shown === rows.length
          ? rows.length.toLocaleString("en") + " branches"
          : shown.toLocaleString("en") + " of " + rows.length.toLocaleString("en") + " branches";
      }}, 120);
    }});
    var t = document.getElementById("theme-toggle");
    t.addEventListener("click", function () {{
      var dark = (document.documentElement.dataset.theme ||
        (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
      document.documentElement.dataset.theme = dark ? "light" : "dark";
      try {{ localStorage.setItem("bdbr-theme", dark ? "light" : "dark"); }} catch (e) {{}}
    }});
  }})();
</script>
</body>
</html>
"""


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    generated = payload["generated"]
    district_by_code: dict[str, str] = {}
    for bank in payload["banks"]:
        for br in bank["branches"]:
            if br["district"]:
                district_by_code.setdefault(br["routing"][3:5], br["district"])

    banks = payload["banks"]
    out_root = SITE / "banks"
    out_root.mkdir(parents=True, exist_ok=True)

    for bank in banks:
        slug = slugify(bank["name"])
        siblings = "".join(
            f'<li><a href="../{slugify(other["name"])}/">{esc(other["name"])}</a>'
            f'<span class="n">{len(other["branches"]):,}</span></li>'
            for other in banks
            if other["code"] != bank["code"]
        )
        page = bank_page(bank, district_by_code, generated).replace("{siblings}", siblings)
        d = out_root / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page, encoding="utf-8")

    # --- sitemap ------------------------------------------------------------
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/banks/{slugify(b['name'])}/" for b in banks]
    sitemap = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{generated}</lastmod>"
        f"<changefreq>monthly</changefreq><priority>{'1.0' if i == 0 else '0.8'}</priority></url>"
        for i, u in enumerate(urls)
    )
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap}\n</urlset>\n",
        encoding="utf-8",
    )

    (SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        "# The dataset is CC0 and the whole point is reuse.\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )

    # --- llms.txt -----------------------------------------------------------
    bank_lines = "\n".join(
        f"- [{b['name']} routing numbers]({SITE_URL}/banks/{slugify(b['name'])}/): "
        f"{len(b['branches']):,} branches, prefix {b['code']}"
        for b in banks
    )
    (SITE / "llms.txt").write_text(
        f"""# {SITE_NAME}

> Bangladesh bank, branch and BEFTN routing-number data with per-bank provenance:
> {payload['counts']['banks']} institutions, {payload['counts']['branches']:,} branches, all
> {payload['counts']['districts']} districts. Every row is traceable to the page it was read
> from and the date it was read. Dataset generated {generated}.

A Bangladeshi routing number is nine digits: bank(3) + district(2) + branch(3) + check(1).
The first three digits ARE the bank and digits 4-5 ARE the district, so a routing number can
be checked against the bank name stored beside it rather than trusted.

## Core

- [Lookup tool and dataset overview]({SITE_URL}/): resolve a routing number, browse all banks
- [Source repository]({REPO_URL}): captures, build, packages, known gaps
- [Known gaps]({REPO_URL}/blob/main/docs/KNOWN-GAPS.md): what is deliberately missing, and why
- [Capture rules]({REPO_URL}/blob/main/docs/CAPTURING.md): how to read a bank's site without getting it wrong

## Packages

- `pip install bd-bank-routing` (imports as `bdbanks`)
- `npm install bd-bank-routing`

## Banks

{bank_lines}

## Author

{AUTHOR_NAME} — {AUTHOR_SITE} — {AUTHOR_GITHUB}
""",
        encoding="utf-8",
    )

    print(f"  wrote site/banks/          {len(banks)} bank pages")
    print(f"        site/sitemap.xml     {len(urls)} urls")
    print("        site/robots.txt")
    print("        site/llms.txt")


if __name__ == "__main__":
    main()
