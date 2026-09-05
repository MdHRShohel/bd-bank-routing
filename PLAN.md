# bd-bank-routing — plan

> Living document. Update as work lands; delete items when shipped.
> **Nothing is published until the owner says so** — no public repo, no PyPI, no npm.

## What this is

A sourced, corroborated directory of Bangladesh's banks, branches and BEFTN
routing numbers — plus the validation logic and the traps that make getting it
wrong so easy.

**63 institutions · 11,426 branches · all 64 districts.**

## Why it should exist

Every BD fintech, payroll and HR product rebuilds this, and rebuilds it badly.
The public options are unsourced scrapes, and they are *demonstrably wrong*: one
widely-referenced dataset files **Commercial Bank of Ceylon under prefix `225`**,
which belongs to **The City Bank** — an error that would send salaries to the
wrong institution. Nothing about it looks wrong until money moves.

What makes this different is not the row count. It is that **every row is
traceable**: each capture file records the URL it came from and the date it was
read, and the whole set is corroborated against the consolidated BACH routing
table — 99.4% agreement, **zero contradictions**.

## What ships

| piece | what it is |
| ----- | ---------- |
| `data/banks.json` | the canonical dataset — one file, versioned |
| `data/sources/` | 63 per-bank captures, each with `# source:` and `# checked:` |
| `packages/python` | `bd-bank-routing` on PyPI (imports as `bdbanks`) — lookup + validation |
| `packages/js` | `bd-bank-routing` on npm — same API, same data |
| `site/` | search a routing, browse banks, see coverage and provenance |

Python and JS are thin wrappers over one canonical JSON. The logic is pure
functions, so the two cannot drift on behaviour, and the data cannot drift at all.

## The library's real value

Not the lookup — anyone can index a JSON file. It is the checks that come from
having got this wrong first:

* **structure** — a BD routing is `bank(3) + district(2) + branch(3) + check(1)`,
  so the first three digits *are* the bank and digits 4–5 *are* the district.
* **prefix ↔ bank agreement** — catches a stored name that disagrees with its own
  routing. This is the `CITIBANK N.A` (075) vs `CITY BANK PLC` (225) class, which
  reached a live payroll record in the product this data came from.
* **settlement endpoints** — `TRUNCATION POINT`, `RTGS-*`, `CLEARING HOUSE`,
  `AGENT BANKING`, `REMITTANCE`, `CARD DIVISION` are in the BACH table and look
  exactly like branches. **A salary cannot be paid into any of them.** 96 were
  selectable in the source product before they were found.
* **lookalike names** — `CITY BANK` / `CITIBANK` / `CITIZENS BANK`, and the three
  different `NRB` banks, which once all shared one stored bank code.
* **retired names** — the picker searches on name, so a bank stored as
  `THE FARMERS BANK LIMITED` cannot be found by someone holding a *Padma Bank*
  cheque book.

## The traps (`docs/CAPTURING.md`)

Worth publishing on its own; each cost real debugging:

* **Pair the name to the routing inside ONE row, never across the page.** A
  page-wide regex over one bank produced 251 plausible pairs, every one wrong —
  each name matched to a *later* row's routing. The count and format both looked
  right.
* **The digits may not be ASCII.** One bank prints `রাউটিং নম্বর: ০৪৭২৭১৫৭১।`, so a
  `[0-9]{9}` scan returns zero and you conclude the bank publishes nothing.
* **Phone numbers look like routings.** `01552490312` contains a valid-looking
  `015…`; `+88 02 2222…` yields `222289152`. Read only the labelled field.
* **A bank's own page can be a subset of its network.** One publishes 70 branches
  and has 147 — trusting the page would delete 39 real ones.
* **Wrapped table rows.** A long branch name pushes its routing onto the next
  line in a PDF, leaving a routing with no name.

## Milestones

- [x] **M1 — data** extract to `data/banks.json` + `data/sources/`; schema; a
      build script that regenerates the JSON from the captures so the sources
      stay the source of truth, not the output.
- [x] **M2 — validation** the checks above as pure functions, ported to both
      languages from one spec, with the real failure cases as tests.
- [x] **M3 — packages** `bdbanks` on PyPI + npm. Not published until approved.
- [x] **M4 — site** routing lookup, bank browser, coverage + provenance view.
      Static HTML/CSS/JS, no framework. `scripts/build_site.py` reshapes the
      1.4 MB dataset into a 3 KB meta file plus a 93 KB (gzipped) branch index,
      and the page derives every district from digits 4–5 rather than reading a
      stored field — so it demonstrates its own opening claim.
- [x] **M4b — discoverability** 63 generated per-bank pages, because nobody
      searches "bd-bank-routing" — they search "sonali bank routing number", and
      a `#/r/...` hash is not a URL anything indexes. Each page carries its bank's
      full branch table in the HTML (no JS needed to read it), Dataset +
      BreadcrumbList JSON-LD, canonical and OG tags. Plus `sitemap.xml`,
      `robots.txt`, `llms.txt`, an FAQ section with FAQPage schema, a generated
      1200x630 OG card, and the author byline pairing shohel.bro.bd with the
      GitHub profile in markup and in `Person.sameAs`.

      ⚠ **Confirm before publishing:** `SITE_URL` in `scripts/seo.py` is the one
      value every canonical, sitemap entry and OG tag is built from. It currently
      says `https://mdhrshohel.github.io/bd-bank-routing`. If the site goes to a
      custom domain instead, change it there and rebuild — a canonical pointing
      at the wrong host is worse than no canonical at all.

- [ ] **M5 — publish** repo public under `MdHRShohel`, then the registries.

## Decisions taken

* **Licence** MIT for code, CC0 for data. CC0 removes every barrier to the
  adoption this is meant to get; ODbL would force share-alike on derived
  datasets, which deters the commercial use that is most of the audience.

* **Name** `bd-bank-routing` on PyPI, npm and GitHub — the phrase people search.
  The Python import stays the shorter `bdbanks`, the way `beautifulsoup4`
  imports as `bs4`.
* **Owner** personal account `MdHRShohel` — this is portfolio and self-branding.
* **Split** data + validator + site in v1. A data-only drop is easy to ignore and
  hard to re-launch.
* **Separate repo**, outside `hrms-serviq`. No dependency either way.

## Open questions

* **Staleness.** A `# checked:` date sets an expectation. The README must say
  plainly that banks open and close branches and this is a snapshot, with the
  date visible per bank — better than implying a freshness nobody is promising.
* **Attribution.** Each capture cites the bank's own site; the corroboration set
  cites the consolidated BACH table as published by Dhaka Bank PLC. Keep both —
  they are the differentiator *and* the honest thing.

## Not in scope

* No data from the product this came from — no employees, orgs, or accounts. The
  captures were checked for it: every match on `employee`/`salary` is explanatory
  prose in a header.
* No scraping service. This is a dataset and a validator, not a crawler people
  point at banks.
