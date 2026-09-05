/**
 * Tests written from the failures that produced this library — every case below
 * happened in a live payroll product, not one invented to exercise a branch.
 *
 * Mirrors the Python suite deliberately: the two packages ship one dataset and
 * must not drift on behaviour either.
 */

import { describe, expect, it } from "vitest";

import {
  bank,
  banks,
  branches,
  check,
  datasetVersion,
  districtOf,
  districts,
  isSettlementEndpoint,
  lookup,
  namesAgree,
} from "./index";

describe("the dataset is sane", () => {
  it("loads", () => {
    expect(datasetVersion()).toBeTruthy();
  });

  it("has Bangladesh's 64 districts, not 65", () => {
    // A dataset claiming 65 is one an informed reader stops trusting.
    expect(districts()).toHaveLength(64);
  });

  it("files every routing under the bank its own first three digits name", () => {
    for (const b of banks()) {
      for (const br of b.branches) {
        expect(br.routing).toMatch(/^\d{9}$/);
        expect(br.routing.startsWith(b.code)).toBe(true);
      }
    }
  });

  it("never lets two banks claim one routing", () => {
    const seen = new Map<string, string>();
    for (const b of banks()) {
      for (const br of b.branches) {
        expect(seen.has(br.routing), `${br.routing} claimed twice`).toBe(false);
        seen.set(br.routing, b.code);
      }
    }
  });

  it("carries provenance on every bank", () => {
    for (const b of banks()) {
      expect(b.source.url).toMatch(/^https?:\/\//);
      expect(b.source.checked).toBeTruthy();
      expect(["first_party", "bach_table"]).toContain(b.source.kind);
    }
  });
});

describe("lookup", () => {
  it("resolves a known routing to bank, branch and district", () => {
    const br = lookup("225150135");
    expect(br?.bankName).toBe("CITY BANK PLC");
    expect(br?.district).toBe("CHATTOGRAM");
  });

  it("returns null for an unknown routing rather than throwing", () => {
    // Banks open branches faster than any dataset updates. Absence is not proof
    // of a fake routing.
    expect(lookup("225999999")).toBeNull();
  });

  it("forgives surrounding whitespace", () => {
    expect(lookup("  225150135 ")).not.toBeNull();
  });
});

describe("the name-versus-routing check", () => {
  // The defect that produced this library: a live payroll record read
  // CITIBANK N.A while the employee banked at CITY BANK PLC.
  it("catches Citibank stored against a City Bank routing", () => {
    const c = check("225150135", "CITIBANK N.A");
    expect(c.ok).toBe(false);
    expect(c.problems.some((p) => p.includes("disagrees"))).toBe(true);
  });

  it("treats Citizens Bank as a different bank too", () => {
    expect(namesAgree("CITIZENS BANK PLC", "CITY BANK PLC")).toBe(false);
  });

  it("accepts a retired corporate form as the same bank", () => {
    // Flagging older records would fire on every one of them, and a checker that
    // cries wolf on legacy data gets switched off.
    expect(namesAgree("THE CITY BANK LIMITED", "CITY BANK PLC")).toBe(true);
    expect(namesAgree("The City Bank Ltd.", "CITY BANK PLC")).toBe(true);
    expect(namesAgree("City Bank", "CITY BANK PLC")).toBe(true);
  });

  it("does not merge different banks when dropping legal form", () => {
    expect(namesAgree("NRB BANK", "NRB COMMERCIAL BANK")).toBe(false);
    expect(namesAgree("ISLAMI BANK BANGLADESH PLC", "GLOBAL ISLAMI BANK PLC")).toBe(false);
  });

  it("does not treat a missing stored name as a disagreement", () => {
    expect(namesAgree(null, "CITY BANK PLC")).toBe(true);
    expect(check("225150135").ok).toBe(true);
  });
});

describe("things that are not branches", () => {
  it("recognises settlement endpoints", () => {
    for (const n of [
      "TRUNCATION POINT",
      "RTGS-INTERBANK LOCAL CURRENCY",
      "DHAKA CLEARING HOUSE",
      "AGENT BANKING",
      "REMITTANCE",
      "CARD DIVISION",
    ]) {
      expect(isSettlementEndpoint(n), n).toBe(true);
    }
  });

  it("does not assume HEAD OFFICE is one", () => {
    // Some head offices are genuinely payable branches, so deciding by regex
    // would be the guess this library exists to replace.
    expect(isSettlementEndpoint("HEAD OFFICE")).toBe(false);
  });

  it("offers no settlement endpoint as a payable branch", () => {
    const offenders = banks({ payableOnly: true })
      .flatMap((b) => b.branches)
      .filter((br) => isSettlementEndpoint(br.name))
      .map((br) => br.routing);
    expect(offenders).toEqual([]);
  });
});

describe("institutions nobody banks at", () => {
  it("flags the central bank as unpayable, with a reason", () => {
    const bb = bank("025");
    expect(bb?.payable).toBe(false);
    expect(bb?.payableReason).toBeTruthy();
  });

  it("explains why when one of its routings is checked", () => {
    const routing = branches("025")[0].routing;
    const c = check(routing);
    expect(c.ok).toBe(false);
    expect(c.problems.some((p) => p.includes("cannot receive a salary"))).toBe(true);
  });

  it("still looks them up rather than hiding them", () => {
    // A lookup should answer, so a caller can explain the problem instead of
    // showing "unknown routing" for a number that plainly exists.
    expect(lookup(branches("025")[0].routing)).not.toBeNull();
  });

  it("excludes them from payableOnly", () => {
    const codes = banks({ payableOnly: true }).map((b) => b.code);
    expect(codes).not.toContain("025");
    expect(codes).not.toContain("405");
  });
});

describe("malformed input", () => {
  it.each(["", "12345", "22515013X", "2251501350"])("reports %s rather than throwing", (bad) => {
    const c = check(bad);
    expect(c.ok).toBe(false);
    expect(c.problems).toContain("not nine digits");
  });

  it("says so when the prefix belongs to no bank", () => {
    expect(check("999150135").problems.some((p) => p.includes("belongs to no bank"))).toBe(true);
  });

  it("distinguishes a known bank with an unknown branch", () => {
    // "the dataset may be behind" and "this bank does not exist" are very
    // different answers to give someone.
    expect(
      check("225999999").problems.some((p) => p.includes("dataset may simply be behind")),
    ).toBe(true);
  });
});

describe("district from the number itself", () => {
  it("reads digits four and five", () => {
    expect(districtOf("225150135")).toBe("CHATTOGRAM");
  });

  it("works for a routing not in the dataset", () => {
    // The point: it answers from structure, not from a lookup.
    expect(lookup("225159999")).toBeNull();
    expect(districtOf("225159999")).toBe("CHATTOGRAM");
  });

  it("returns null for malformed input", () => {
    expect(districtOf("nope")).toBeNull();
  });
});
