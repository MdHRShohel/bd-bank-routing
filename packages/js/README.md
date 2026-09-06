# bd-bank-routing

**Bangladesh bank routing numbers, branches and districts — with the receipts.**

**→ [Look one up](https://mdhrshohel.github.io/bd-bank-routing/)**

Look up any BD bank routing number, or check that the one you already store is
real, payable, and actually belongs to the bank whose name sits next to it.

63 institutions · 11,426 branches · all 64 districts · every row traceable to the
page it was read from and the date it was read.

```
routing  225150135
         └─┬─┘└┬┘└┬┘│
           │   │  │ └── check digit
           │   │  └──── branch
           │   └─────── district   (15 = Chattogram)
           └─────────── bank       (225 = City Bank PLC)
```

## Why this exists

Every Bangladeshi fintech, payroll and HR product rebuilds this, and rebuilds it
badly. The public datasets are unsourced scrapes — and they are *demonstrably
wrong*. One widely-referenced set files **Commercial Bank of Ceylon under prefix
`225`**, which belongs to **The City Bank**. Nothing about that looks wrong in a
dropdown. It looks wrong when a salary lands in the wrong institution.

This is not a bigger scrape. It is a dataset where you can always answer *where
did this row come from, and when was it last checked?* — with a library that
encodes the mistakes that are easy to make and expensive to find.

## Install

```bash
pip install bd-bank-routing      # Python
npm install bd-bank-routing      # JavaScript / TypeScript  (also yarn / pnpm / bun)
```

> **npm is live; PyPI is not published yet.** `npm install bd-bank-routing`
> works today. The Python package builds, installs and passes its suite — see
> [docs/PUBLISHING.md](docs/PUBLISHING.md) — but is not on PyPI yet. Until it is,
> take `data/banks.json` directly, or use the site above.

```python
import bdbanks                                   # short import, like bs4

bdbanks.lookup("225150135")
# Branch(routing='225150135', name='Agrabad Branch', district='CHATTOGRAM',
#        bank_code='225', bank_name='CITY BANK PLC', payable=True)

bdbanks.check("225150135", bank_name="Citibank N.A").problems
# ["stored bank name 'Citibank N.A' disagrees with routing 225150135
#   (prefix 225 is 'CITY BANK PLC')"]
```

```ts
import { lookup, check } from "bd-bank-routing";

lookup("225150135")?.bankName;          // "CITY BANK PLC"
check("225150135", "Citibank N.A").ok;  // false
```

Or take `data/banks.json` and use it however you like — it is the same file both
packages ship, and it has no dependencies of its own.

*(The install name spells out what people search for; the Python import is the
shorter `bdbanks`, the way `beautifulsoup4` imports as `bs4`.)*

## What it catches

The lookup is the boring part. These are the checks that come from getting it
wrong first, in production:

**The name disagrees with the routing.** A record read `CITIBANK N.A`; the
employee banked at `CITY BANK PLC`. Two different banks, four characters apart,
sitting on a live payroll record. The routing settles it without anyone noticing
anything — the first three digits *are* the bank.

**It is not a branch at all.** `TRUNCATION POINT`, `RTGS-*`, `CLEARING HOUSE`,
`AGENT BANKING`, `REMITTANCE` and `CARD DIVISION` appear in the official routing
table and look exactly like branches in a dropdown. **A salary cannot be paid
into any of them.** Ninety-six were selectable in the product this came from
before anyone noticed.

**The institution cannot receive a salary.** Bangladesh Bank's 35 clearing points
and the Controller General of Accounts' 11 ministry units are real routing
numbers that no employee holds an account at. They are included here — flagged —
so a lookup answers, and so you can refuse to *offer* them.

**Lookalikes.** `CITY BANK` / `CITIBANK` / `CITIZENS BANK`. Three different `NRB`
banks that once all shared one stored bank code.

**Retired names.** If you store `THE FARMERS BANK LIMITED`, nobody holding a
*Padma Bank* cheque book will find it by typing what is on the cheque.

## Provenance

Each bank in `data/sources/` carries the URL it was read from and the date:

```
# source: https://www.citybankplc.com/locator?type=Branch
# checked: 2026-09-04
# name: CITY BANK PLC
```

Two kinds of source, and the difference is recorded per bank rather than blurred:

| kind | meaning | count |
| ---- | ------- | ----- |
| `first_party` | read from the bank's own website | 31 |
| `bach_table` | the consolidated BACH routing table (26.06.2025), published by Dhaka Bank PLC | 32 |

The BACH table is used **additively**, for banks that publish no routing numbers
themselves. It is a June-2025 snapshot, so it is never treated as authority for a
branch being *absent*.

Cross-checking the whole set against it: **99.4% corroborated, zero
contradictions** — no routing is filed under a different bank than we file it
under.

## Honesty about staleness

Banks open, close and rename branches. This is a snapshot, and every bank shows
the date it was checked so you can judge for yourself. It does not promise a
freshness nobody is maintaining. If a branch is missing or wrong, the capture
files are plain text — open an issue with the bank's own page and it can be
fixed in one line.

## What is not here

Fourteen branches that banks list on their sites without publishing a routing
number, one where a bank publishes another bank's prefix, and one routing whose
branch name no source can establish. They are recorded
in `docs/KNOWN-GAPS.md` rather than guessed at. **An invented routing number does
not fail — it pays a real account belonging to someone else.**

## Reading a bank's site without getting it wrong

`docs/CAPTURING.md` is the part that cost the most to learn:

- **Pair the name to the routing inside one row, never across the page.** A
  page-wide regex over one bank produced 251 plausible pairs, every one wrong —
  each name matched to a *later* row's routing. The count looked right. The
  format looked right.
- **The digits may not be ASCII.** One bank prints `রাউটিং নম্বর: ০৪৭২৭১৫৭১।`, so a
  `[0-9]{9}` scan returns zero and you conclude it publishes nothing.
- **Phone numbers look like routings.** `01552490312` contains a plausible
  `015…`; `+88 02 2222…` yields `222289152`.
- **A bank's own page can be a subset of its own network.** One publishes 70
  branches and has 147. Trusting the page would delete 39 real ones.

## The site

`site/` is a static page — no framework, no build step — that does the lookup in
the browser: paste a routing number and watch it come apart into bank, district,
branch and check digit, with the source and check-date of whichever bank it
resolves to.

```bash
./scripts/check.sh                # build everything + run both test suites
cd site && python3 -m http.server # then open http://localhost:8000
```

Alongside it the build writes a page per bank — `site/banks/<bank>/` — with
that bank's whole branch table in the HTML, so the rows are readable (and
indexable) with JavaScript switched off. A hash route cannot be indexed, and
nobody searches for this project by name; they search for their bank.

It never downloads `banks.json`. `scripts/build_site.py` splits it into a 3 KB
metadata file and a `routing|name` index that gzips to about 93 KB, and the page
derives every district from digits 4–5 rather than reading a stored field — so
the page is a demonstration of the claim it opens with, not a restatement of it.

## Licence

Code **MIT**. Data **CC0** — routing numbers are public facts, and the point is
for people to use them without asking.

Sources are cited per bank because it is both the differentiator and the right
thing to do.
