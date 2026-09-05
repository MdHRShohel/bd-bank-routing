/**
 * Bangladesh bank, branch and BEFTN routing data — with the receipts.
 *
 * A BD routing number is nine digits and every part means something:
 *
 *     225150135
 *     └─┬─┘└┬┘└┬┘│
 *       │   │  │ └── check digit
 *       │   │  └──── branch
 *       │   └─────── district   (15 = Chattogram)
 *       └─────────── bank       (225 = City Bank PLC)
 *
 * So a routing number is not an opaque token to store beside a bank name — it
 * *is* the bank and the district, and can be checked against both. Most of this
 * module exists because that check was missing somewhere and cost real money.
 *
 * ```ts
 * import { lookup, check } from "bdbanks";
 * lookup("225150135");                              // → CITY BANK PLC, Agrabad Branch
 * check("225150135", "Citibank N.A").ok;            // → false
 * ```
 */

import dataset from "./dataset.js";

/** Wording that marks a BACH settlement endpoint rather than a branch anyone
 *  banks at. `HEAD OFFICE` is deliberately absent — some head offices are
 *  genuinely payable branches, so a regex there would be a guess. */
const SETTLEMENT =
  /truncation\s+point|rtgs|clearing\s+house|agent\s+banking|remittance|card\s+division|interbank/i;

/** Words naming a company's legal form, not which company it is. Dropped before
 *  comparing names: the Companies Act turned most "Limited" into "PLC", and a
 *  checker that reports `THE CITY BANK LIMITED` against `CITY BANK PLC` fires on
 *  every older record and gets switched off. */
const CORPORATE_FORM = /\b(THE|LIMITED|LTD|PLC|COMPANY|CO|INCORPORATED|INC)\b\.?/gi;

export interface Branch {
  readonly routing: string;
  readonly name: string;
  readonly district: string | null;
  readonly bankCode: string;
  readonly bankName: string;
  readonly payable: boolean;
}

export interface Bank {
  readonly code: string;
  readonly name: string;
  readonly payable: boolean;
  readonly payableReason?: string;
  readonly source: { url: string; checked: string; kind: "first_party" | "bach_table" };
  readonly branches: readonly Branch[];
}

export interface Check {
  readonly routing: string;
  readonly ok: boolean;
  readonly problems: readonly string[];
  readonly branch: Branch | null;
}

interface RawBank {
  code: string;
  name: string;
  payable: boolean;
  payable_reason?: string;
  source: { url: string; checked: string; kind: "first_party" | "bach_table" };
  branches: { routing: string; name: string; district: string | null }[];
}

const RAW = dataset as unknown as {
  generated: string;
  districts: string[];
  banks: RawBank[];
};

const BANKS: readonly Bank[] = RAW.banks.map((b) => {
  const bank: Bank = {
    code: b.code,
    name: b.name,
    payable: b.payable,
    payableReason: b.payable_reason,
    source: b.source,
    branches: b.branches.map((br) => ({
      routing: br.routing,
      name: br.name,
      district: br.district,
      bankCode: b.code,
      bankName: b.name,
      payable: b.payable,
    })),
  };
  return bank;
});

const BY_CODE = new Map(BANKS.map((b) => [b.code, b]));
const BY_ROUTING = new Map<string, Branch>();
for (const b of BANKS) for (const br of b.branches) BY_ROUTING.set(br.routing, br);

/** The date the bundled dataset was generated. */
export function datasetVersion(): string {
  return RAW.generated;
}

/**
 * The branch a routing number belongs to, or `null` if it is not in the set.
 *
 * `null` is not proof a routing is fake — banks open branches faster than any
 * dataset is updated. Use {@link check} to tell "unknown" from "malformed".
 */
export function lookup(routing: string): Branch | null {
  return BY_ROUTING.get(String(routing ?? "").trim()) ?? null;
}

export function banks(options: { payableOnly?: boolean } = {}): readonly Bank[] {
  return options.payableOnly ? BANKS.filter((b) => b.payable) : BANKS;
}

export function bank(code: string): Bank | null {
  return BY_CODE.get(String(code ?? "").trim()) ?? null;
}

export function branches(bankCode: string): readonly Branch[] {
  return bank(bankCode)?.branches ?? [];
}

/** All 64 districts of Bangladesh, as they appear in the data. */
export function districts(): readonly string[] {
  return RAW.districts;
}

/**
 * The district a routing number's own digits point at (positions 4–5).
 *
 * Works for routings not in the dataset, which is the point: it answers from the
 * number's structure rather than from a lookup.
 */
export function districtOf(routing: string): string | null {
  const r = String(routing ?? "").trim();
  if (!/^\d{9}$/.test(r)) return null;
  const code = r.slice(3, 5);
  for (const br of BY_ROUTING.values()) {
    if (br.routing.slice(3, 5) === code && br.district) return br.district;
  }
  return null;
}

/**
 * Is this a BACH settlement point rather than a place a salary can go?
 *
 * `TRUNCATION POINT`, `RTGS-*`, `CLEARING HOUSE`, `AGENT BANKING`, `REMITTANCE`
 * and `CARD DIVISION` sit in the official routing table and look exactly like
 * branches in a dropdown.
 */
export function isSettlementEndpoint(branchName: string): boolean {
  return SETTLEMENT.test(branchName ?? "");
}

function normalise(name: string | null | undefined): string {
  return (name ?? "").toUpperCase().replace(CORPORATE_FORM, " ").replace(/[^A-Z0-9]/g, "");
}

/**
 * Do two bank names refer to the same institution?
 *
 * Loose about legal form and punctuation — `City Bank`, `THE CITY BANK LIMITED`
 * and `CITY BANK PLC` are one bank. Strict about identity: `CITIBANK N.A` is
 * not, and neither is `CITIZENS BANK PLC`.
 */
export function namesAgree(stored: string | null | undefined, official: string | null | undefined): boolean {
  const a = normalise(stored);
  const b = normalise(official);
  if (!a || !b) return true; // nothing stored cannot disagree
  return a.includes(b) || b.includes(a);
}

/**
 * Validate a routing number, and optionally the bank name stored beside it.
 *
 * Reports every problem rather than the first, because a caller fixing a record
 * wants the whole list.
 */
export function check(routing: string, bankName?: string | null): Check {
  const r = String(routing ?? "").trim();
  if (!/^\d{9}$/.test(r)) {
    return { routing: r, ok: false, problems: ["not nine digits"], branch: null };
  }

  const br = lookup(r);
  if (!br) {
    const known = new Set(BANKS.map((b) => b.code));
    return {
      routing: r,
      ok: false,
      problems: [
        known.has(r.slice(0, 3))
          ? "not a known branch (the dataset may simply be behind)"
          : `prefix ${r.slice(0, 3)} belongs to no bank in the dataset`,
      ],
      branch: null,
    };
  }

  const problems: string[] = [];
  if (!br.payable) {
    problems.push(
      `${br.bankName} cannot receive a salary — ${bank(br.bankCode)?.payableReason ?? ""}`.trim(),
    );
  }
  if (isSettlementEndpoint(br.name)) {
    problems.push(
      `"${br.name}" is a settlement endpoint, not a branch — no salary can be paid into it`,
    );
  }
  if (bankName != null && !namesAgree(bankName, br.bankName)) {
    problems.push(
      `stored bank name "${bankName}" disagrees with routing ${r} ` +
        `(prefix ${r.slice(0, 3)} is "${br.bankName}")`,
    );
  }

  return { routing: r, ok: problems.length === 0, problems, branch: br };
}
