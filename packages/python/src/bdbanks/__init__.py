"""Bangladesh bank, branch and BEFTN routing data — with the receipts.

A BD routing number is nine digits and every part of it means something::

    225150135
    └─┬─┘└┬┘└┬┘│
      │   │  │ └── check digit
      │   │  └──── branch
      │   └─────── district   (15 = Chattogram)
      └─────────── bank       (225 = City Bank PLC)

So the routing number is not an opaque token to store beside a bank name — it
*is* the bank and the district, and it can be checked against both. Most of this
module exists because that check was missing somewhere and cost real money.

    >>> import bdbanks
    >>> b = bdbanks.lookup("225150135")
    >>> b.bank_name, b.branch_name, b.district
    ('CITY BANK PLC', 'Agrabad Branch', 'CHATTOGRAM')

    >>> bdbanks.check("225150135", bank_name="Citibank N.A").ok
    False
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files
from typing import Iterator

__all__ = [
    "Branch",
    "Bank",
    "Check",
    "lookup",
    "check",
    "banks",
    "bank",
    "branches",
    "districts",
    "district_of",
    "is_settlement_endpoint",
    "names_agree",
    "dataset_version",
]

#: Wording that marks a BACH settlement endpoint rather than a branch anyone
#: banks at. `HEAD OFFICE` is deliberately absent: some head offices are
#: genuinely payable branches, so a regex there would be a guess.
_SETTLEMENT = re.compile(
    r"truncation\s+point|rtgs|clearing\s+house|agent\s+banking"
    r"|remittance|card\s+division|interbank",
    re.IGNORECASE,
)

#: Words that name a company's legal form, not which company it is. Dropped
#: before comparing names, because the Companies Act turned most "Limited" into
#: "PLC" and a checker that reports `THE CITY BANK LIMITED` against
#: `CITY BANK PLC` fires on every older record and gets switched off.
_CORPORATE_FORM = re.compile(
    r"\b(THE|LIMITED|LTD|PLC|COMPANY|CO|INCORPORATED|INC)\b\.?", re.IGNORECASE
)


@dataclass(frozen=True)
class Branch:
    """One payable destination."""

    routing: str
    name: str
    district: str | None
    bank_code: str
    bank_name: str
    payable: bool

    @property
    def is_settlement_endpoint(self) -> bool:
        return is_settlement_endpoint(self.name)


@dataclass(frozen=True)
class Bank:
    code: str
    name: str
    payable: bool
    source_url: str
    checked: str
    source_kind: str
    payable_reason: str | None = None
    branches: tuple[Branch, ...] = field(default=(), repr=False)


@dataclass(frozen=True)
class Check:
    """The result of validating a routing number, and optionally a name with it.

    Falsy when anything failed, so `if not check(...)` reads naturally.
    """

    routing: str
    ok: bool
    problems: tuple[str, ...]
    branch: Branch | None = None

    def __bool__(self) -> bool:
        return self.ok


@lru_cache(maxsize=1)
def _data() -> dict:
    raw = files("bdbanks").joinpath("banks.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def _index() -> dict[str, Branch]:
    out: dict[str, Branch] = {}
    for b in _data()["banks"]:
        for br in b["branches"]:
            out[br["routing"]] = Branch(
                routing=br["routing"],
                name=br["name"],
                district=br["district"],
                bank_code=b["code"],
                bank_name=b["name"],
                payable=b["payable"],
            )
    return out


@lru_cache(maxsize=1)
def _banks() -> dict[str, Bank]:
    out: dict[str, Bank] = {}
    for b in _data()["banks"]:
        out[b["code"]] = Bank(
            code=b["code"],
            name=b["name"],
            payable=b["payable"],
            source_url=b["source"]["url"],
            checked=b["source"]["checked"],
            source_kind=b["source"]["kind"],
            payable_reason=b.get("payable_reason"),
            branches=tuple(
                Branch(
                    routing=br["routing"],
                    name=br["name"],
                    district=br["district"],
                    bank_code=b["code"],
                    bank_name=b["name"],
                    payable=b["payable"],
                )
                for br in b["branches"]
            ),
        )
    return out


def dataset_version() -> str:
    """The date the bundled dataset was generated."""
    return _data()["generated"]


def lookup(routing: str) -> Branch | None:
    """The branch a routing number belongs to, or None if it is not in the set.

    Returning None is not proof a routing is fake — banks open branches faster
    than any dataset is updated. Use :func:`check` to tell "unknown" apart from
    "malformed".
    """
    return _index().get(str(routing).strip())


def banks(payable_only: bool = False) -> list[Bank]:
    out = sorted(_banks().values(), key=lambda b: b.code)
    return [b for b in out if b.payable] if payable_only else out


def bank(code: str) -> Bank | None:
    return _banks().get(str(code).strip())


def branches(bank_code: str) -> tuple[Branch, ...]:
    b = bank(bank_code)
    return b.branches if b else ()


def districts() -> list[str]:
    """All 64 districts of Bangladesh, as they appear in the data."""
    return list(_data()["districts"])


def district_of(routing: str) -> str | None:
    """The district a routing number's own digits point at (positions 4-5).

    Works for routings not in the dataset, which is the point: it answers from
    the number's structure rather than from a lookup.
    """
    r = str(routing).strip()
    if not re.fullmatch(r"\d{9}", r):
        return None
    code = r[3:5]
    for br in _index().values():
        if br.routing[3:5] == code and br.district:
            return br.district
    return None


def is_settlement_endpoint(branch_name: str) -> bool:
    """Is this a BACH settlement point rather than a place a salary can go?

    `TRUNCATION POINT`, `RTGS-*`, `CLEARING HOUSE`, `AGENT BANKING`,
    `REMITTANCE`, `CARD DIVISION` sit in the official routing table and look
    exactly like branches in a dropdown.
    """
    return bool(_SETTLEMENT.search(branch_name or ""))


def _normalise(name: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", _CORPORATE_FORM.sub(" ", (name or "").upper()))


def names_agree(stored: str | None, official: str | None) -> bool:
    """Do two bank names refer to the same institution?

    Loose about legal form and punctuation — `City Bank`, `THE CITY BANK LIMITED`
    and `CITY BANK PLC` are one bank. Strict about identity: `CITIBANK N.A` is
    not, and neither is `CITIZENS BANK PLC`.
    """
    a, b = _normalise(stored), _normalise(official)
    if not a or not b:
        return True  # nothing stored cannot disagree
    return a in b or b in a


def check(routing: str, bank_name: str | None = None) -> Check:
    """Validate a routing number, and optionally the bank name stored beside it.

    Reports every problem it finds rather than the first, because a caller
    fixing a record wants the whole list.
    """
    r = str(routing).strip()
    problems: list[str] = []

    if not re.fullmatch(r"\d{9}", r):
        return Check(r, False, ("not nine digits",), None)

    br = lookup(r)
    if br is None:
        known = {b.code for b in banks()}
        if r[:3] not in known:
            problems.append(f"prefix {r[:3]} belongs to no bank in the dataset")
        else:
            problems.append("not a known branch (the dataset may simply be behind)")
        return Check(r, False, tuple(problems), None)

    if not br.payable:
        problems.append(
            f"{br.bank_name} cannot receive a salary — "
            f"{bank(br.bank_code).payable_reason}"
        )
    if br.is_settlement_endpoint:
        problems.append(
            f"{br.name!r} is a settlement endpoint, not a branch — no salary can be paid into it"
        )
    if bank_name is not None and not names_agree(bank_name, br.bank_name):
        problems.append(
            f"stored bank name {bank_name!r} disagrees with routing {r} "
            f"(prefix {r[:3]} is {br.bank_name!r})"
        )

    return Check(r, not problems, tuple(problems), br)


def __iter__() -> Iterator[Bank]:  # pragma: no cover - convenience only
    return iter(banks())
