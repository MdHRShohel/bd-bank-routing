# Known gaps

What is missing, and why it is missing rather than guessed at.

**An invented routing number does not fail.** It is well-formed, it passes every
structural check, and it pays a real account belonging to someone else. So where
the evidence runs out, the row is left out and recorded here.

---

## Branches a bank lists without publishing a routing (11)

**Bengal Commercial Bank PLC (`315`)** lists 37 branches on its own site by
email address, but publishes a routing number for only 26 of them. The other
eleven have a card, an address and a mailbox — and no number:

`ashkona` · `ashulia` · `dupchanchia` · `haragach` · `kamrangirchar` · `karwan` ·
`khatunganj` · `namabazar` · `poddarbazar` · `rampura` · `tongi`

They are not in the consolidated routing table either. Someone banking at one of
these cannot be looked up here.

**What would close it:** the bank publishing the numbers, or a written reply.

---

## A bank publishing another bank's prefix (1)

**United Commercial Bank PLC (`245`)** prints `215761333` for its **Kashinathpur
Branch**. `215` is **Standard Chartered Bank** — a UCB branch cannot hold a
Standard Chartered routing.

The district digits (`76` = Pabna) are correct and Kashinathpur is in Pabna, so
the branch is real and only the prefix is wrong. The obvious repair would be
`245761333`, and that number appears in **no source held here**. Re-checked
2026-09-05: UCB's locator still prints the wrong prefix, and their site carries
no second branch list.

**What would close it:** UCB correcting the page, or the number appearing in a
routing table.

---

## A routing whose branch name cannot be established (1)

**Shahjalal Islami Bank PLC (`190`)** — `190220253`.

It was carried here as `UTTARA LADIES BRANCH`, in Dhaka. Its own digits 4–5
(`22`) say **Cox's Bazar**, so the name and the number disagreed about where the
branch is.

The bank's page settles which half is wrong. The mailbox
`uttaraladies@sjiblbd.com` belongs to **Garib-E-Newaz Avenue Branch**, routing
`190260068`, in Uttara, Dhaka — a branch this dataset already carries under that
current name. So `UTTARA LADIES BRANCH` is a **retired name for a different
routing**, and it had been paired to this one. Precisely
[RULE 0](CAPTURING.md#rule-0--pair-the-name-to-the-routing-inside-one-row-never-across-the-page).

`190220253` is real — the BACH table carries it, and `190` is Shahjalal — so it
is a Cox's Bazar branch of this bank. But the BACH capture stores **routings
only, deliberately**, so nothing here can name it, and the bank's own page is a
known subset that omits it. The row is therefore out rather than renamed.

A lookup on `190220253` now answers *"not a known branch (the dataset may simply
be behind)"*, which is true, instead of naming a Dhaka branch that is somewhere
else.

**What would close it:** the branch appearing on the bank's own page.

---

## Branches carried here that the bank no longer lists (13)

Ten Pubali, one Sonali, one Southeast, one ICB Islamic, one City Bank.

These are **kept**, not deleted. Deleting a branch that is actually open makes
someone unpayable and orphans an account already saved against it. Keeping one
that has closed fails later at BEFTN validation — visibly, at submission — and
cannot misroute money, because routing numbers are not reused.

Each is named in its bank's capture file under `RETAINED vs the bank's list`.

**What would close it:** confirmation from each bank that the branch has closed.

---

## Scheduled banks not carried at all (3)

On Bangladesh Bank's scheduled-bank list, absent here because **no source exists
for their routing numbers**:

| bank | why |
| ---- | --- |
| **Probashi Kollyan Bank** | its own site lists 80 branches with manager contacts and **no routing numbers**, in either ASCII or Bengali digits — checked both |
| **Nagad Digital Bank PLC.** | a digital bank; may have no conventional branches at all |
| **Sammilito Islami Bank PLC** | the entity the five-bank Islamic merger created. Its five constituents are still listed separately, so its routings may not exist yet |

None appears in the consolidated routing table either — checked, zero matches
for each.

Someone banking at one of these cannot be looked up here. That is a real gap,
not a rounding error, and it is stated rather than papered over.

**What would close it:** the bank publishing a branch list with routing numbers,
or a later edition of the routing table carrying the prefix.

---

## Banks that cannot be checked against themselves (5)

These publish branch **locations** but not BEFTN routing numbers, so their rows
here come from the consolidated table rather than the bank:

`Standard Chartered` · `Habib Bank` · `National Bank of Pakistan` ·
`Bank Al-Falah` · `Citibank N.A`

Standard Chartered's was verified at its data source — the JSON its own locator
reads — which carries `id`, `name`, `address`, `services` and `telephone`, and no
routing field at all. National Bank of Pakistan's branch page returns a server
error (`Call to undefined function mysql_query()`). Habib's renders "Loading…"
and fetches its list by JavaScript with no discoverable endpoint.

**This is not a coverage gap.** All five are exactly corroborated against the
routing table. They simply cannot be settled against themselves, which is a
weaker problem than being incomplete — and the distinction is recorded per bank
as `source.kind`.
