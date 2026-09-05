# Reading a bank's site without getting it wrong

Every rule here is one that produced wrong data first. They are ordered by how
badly they bite, not by how likely they are.

The output format is one file per bank, `<code>_<name>.txt`:

```
# source: https://www.citybankplc.com/locator?type=Branch
# checked: 2026-09-04
# name: CITY BANK PLC
225060283|Barisal Branch|BARISHAL
225090103|Bhola Branch|BHOLA
```

The header is not decoration. A row you cannot re-check is worth no more than
the scrape it replaced.

---

## Rule 0 — pair the name to the routing inside ONE row, never across the page

**This is the only mistake that has happened twice, and it fails silently.** The
count comes out right. The format comes out right. Every pair is wrong.

Matching `\d{9}` across a whole locator page gave one bank's Agrabad routing to
all five branches sampled. A page-wide regex over
`title="<name>" … <small>250nnnnnn</small>` for another produced **251 pairs,
every one wrong** — each name matched to a *later* row's routing. It gave a Dhaka
branch a Bagerhat routing and handed two different branches the same number.

So: split the document into rows or cards **first** — `<tr>`, the card element,
the `<td>` — then read the name and the routing out of that one fragment.

**Then check it.** Digits 4–5 are the district. Take branches whose district you
can name from the branch name alone — `Bagerhat Branch`, `Sylhet Branch`,
`Teknaf Branch` — and confirm the digits agree. Nothing about the output's shape
will tell you; only this will.

---

## Rule 0b — the digits may not be ASCII

A `\b[0-9]{9}\b` scan returning **zero** does not mean the bank publishes no
routing numbers.

Bangladesh Development Bank publishes every branch's routing as
`রাউটিং নম্বর: ০৪৭২৭১৫৭১।` — fifty-two of them. An ASCII scan found none, and the
bank was written off as publishing nothing and taken from a third-party table
instead. Settling against the bank afterwards confirmed all 51 rows from that
table *and* added one it lacked.

```python
BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
text = raw.translate(BN)
```

Search `রাউটিং` as well as `routing` before concluding a page carries neither.

**Names, though, stay in the source's own script.** Transliterating a Bengali
branch name into English invents a spelling. Prefer an English field the page
already carries — BDBL's branch emails (`madaripur@bdbl.com.bd`) give the name
directly.

---

## Rule 1 — a nine-digit run is not a routing number

Phone numbers look exactly like them.

- Al-Arafah's bank code is `015`, and Bangladeshi mobiles start `01…`. The
  branch phone `01552490312` yields a perfectly plausible `015524903`.
- State Bank of India's page carries `Tel: +88 02 2222…`, which yields
  `222289152`, `222280469`, `222289153`.
- Bengal Commercial's footer holds `+880-255068880` — inside an HTML comment.

Read only the **labelled** field: `Routing Number:`, `রাউটিং নম্বর`, or the column
under that header. Never scan the page for digits.

---

## Rule 2 — a bank's own page can be a subset of its own network

The general rule is that the bank's site outranks any third party. Shahjalal
Islami is the exception that proves it needs checking: its page publishes **70**
branches and its real network is **147**. Applying the page as truth would have
deleted 39 real branches and still left 35 missing.

So when a bank's page disagrees with a wider source, ask which direction the
disagreement runs. Extra rows on the page are a correction. Missing rows may be
a subset.

---

## Rule 3 — some rows are not branches at all

`TRUNCATION POINT`, `RTGS-INTERBANK FOREX TRANSACTIONS`, `RTGS-INTERBANK LOCAL
CURRENCY`, `CLEARING HOUSE`, `AGENT BANKING`, `REMITTANCE` and `CARD DIVISION`
appear in the official routing table and look exactly like branches in a
dropdown. **A salary cannot be paid into any of them.**

Ninety-six were selectable across 53 banks in the product this came from.

`HEAD OFFICE` is **not** on that list, deliberately. Some head offices are
genuinely payable branches — Sonali's is — so removing them by pattern would be
the same class of guess this whole exercise exists to replace. Settle each bank
against its own list instead.

---

## Rule 4 — a long name wraps and takes the routing with it

In the consolidated PDF table, `RTGS-INTERBANK FOREX TRANSACTIONS` is long
enough that the routing is pushed onto the **next line**, leaving a routing with
a blank name. Read only that line and you file a settlement endpoint as an
unnamed branch.

If a line holds a routing and nothing else, the name is on the line above.

---

## Rule 5 — the district column is often not the district

Banks print `DHAKA-NORTH` / `DHAKA-SOUTH` (clearing zones, not districts), and
retired spellings: `BARISAL`, `COMILLA`, `JESSORE`, `CHITTAGONG`, `BOGRA`.

Derive the district from **digits 4–5 of the routing** against a corpus you
already trust, then use the page's own column to break ties where a code is
ambiguous. That ordering matters: the routing is authoritative, the column is
corroboration.

Bangladesh has **64** districts. A dataset with 65 has an unnormalised alias in
it, and the build here fails rather than shipping one.

---

## Rule 6 — check the bank's identity, not just the branch's

The first three digits **are** the bank. A capture whose routings are not all on
its own prefix is either the wrong file or the wrong bank.

United Commercial Bank's locator prints `215761333` for its Kashinathpur branch.
`215` is **Standard Chartered**. The district digits (`76`, Pabna) are right, so
the branch is real and only the prefix is wrong — but the obvious repair,
`245761333`, appears in no source. It is left out and recorded, because **an
invented routing number does not fail; it pays a real account belonging to
someone else.**
