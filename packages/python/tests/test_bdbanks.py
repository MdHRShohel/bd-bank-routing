"""Tests written from the failures that produced this library.

Every case below is something that actually happened in a live payroll product,
not a case invented to exercise a branch.
"""

from __future__ import annotations

import bdbanks
import pytest


class TestTheDatasetIsSane:
    def test_it_loads(self):
        assert bdbanks.dataset_version()

    def test_bangladesh_has_sixty_four_districts(self):
        """A dataset claiming 65 is one an informed reader stops trusting."""
        assert len(bdbanks.districts()) == 64

    def test_every_routing_is_nine_digits_on_its_own_bank_prefix(self):
        for b in bdbanks.banks():
            for br in b.branches:
                assert len(br.routing) == 9 and br.routing.isdigit(), br
                assert br.routing.startswith(b.code), (
                    f"{br.routing} is filed under {b.code} but its own first three "
                    "digits say otherwise — the prefix IS the bank"
                )

    def test_no_routing_is_claimed_by_two_banks(self):
        seen: dict[str, str] = {}
        for b in bdbanks.banks():
            for br in b.branches:
                assert br.routing not in seen, f"{br.routing}: {seen.get(br.routing)} vs {b.code}"
                seen[br.routing] = b.code

    def test_every_bank_carries_its_provenance(self):
        for b in bdbanks.banks():
            assert b.source_url.startswith("http"), b.code
            assert b.checked, b.code
            assert b.source_kind in {"first_party", "bach_table"}, b.code


class TestLookup:
    def test_a_known_routing_resolves_to_bank_branch_and_district(self):
        br = bdbanks.lookup("225150135")
        assert br is not None
        assert br.bank_name == "CITY BANK PLC"
        assert br.district == "CHATTOGRAM"

    def test_an_unknown_routing_is_none_not_an_error(self):
        """Banks open branches faster than any dataset updates. Absence is not
        proof of a fake routing, so this must not raise."""
        assert bdbanks.lookup("225999999") is None

    def test_whitespace_is_forgiven(self):
        assert bdbanks.lookup("  225150135 ") is not None


class TestTheNameVersusRoutingCheck:
    """The defect that produced this library: a live payroll record read
    CITIBANK N.A while the employee banked at CITY BANK PLC."""

    def test_citibank_stored_against_a_city_bank_routing_is_caught(self):
        c = bdbanks.check("225150135", bank_name="CITIBANK N.A")
        assert not c
        assert any("disagrees" in p for p in c.problems)

    def test_citizens_bank_is_also_a_different_bank(self):
        assert not bdbanks.names_agree("CITIZENS BANK PLC", "CITY BANK PLC")

    def test_a_retired_corporate_form_is_the_same_bank(self):
        """The Companies Act turned most Limited into PLC. Flagging older records
        would fire on every one of them, and a checker that cries wolf on legacy
        data gets switched off."""
        assert bdbanks.names_agree("THE CITY BANK LIMITED", "CITY BANK PLC")
        assert bdbanks.names_agree("The City Bank Ltd.", "CITY BANK PLC")
        assert bdbanks.names_agree("City Bank", "CITY BANK PLC")

    def test_dropping_legal_form_does_not_merge_different_banks(self):
        assert not bdbanks.names_agree("NRB BANK", "NRB COMMERCIAL BANK")
        assert not bdbanks.names_agree("ISLAMI BANK BANGLADESH PLC", "GLOBAL ISLAMI BANK PLC")

    def test_no_stored_name_is_not_a_disagreement(self):
        assert bdbanks.names_agree(None, "CITY BANK PLC")
        assert bdbanks.check("225150135").ok


class TestThingsThatAreNotBranches:
    def test_settlement_endpoints_are_recognised(self):
        for name in (
            "TRUNCATION POINT",
            "RTGS-INTERBANK LOCAL CURRENCY",
            "DHAKA CLEARING HOUSE",
            "AGENT BANKING",
            "REMITTANCE",
            "CARD DIVISION",
        ):
            assert bdbanks.is_settlement_endpoint(name), name

    def test_head_office_is_not_assumed_to_be_one(self):
        """Some head offices are genuinely payable branches, so deciding by regex
        would be the guess this library exists to replace."""
        assert not bdbanks.is_settlement_endpoint("HEAD OFFICE")

    def test_a_real_branch_is_not_one(self):
        assert not bdbanks.is_settlement_endpoint("Agrabad Branch")

    def test_the_dataset_offers_no_settlement_endpoint_as_a_payable_branch(self):
        offenders = [
            (b.code, br.name)
            for b in bdbanks.banks(payable_only=True)
            for br in b.branches
            if br.is_settlement_endpoint
        ]
        assert offenders == [], f"selectable settlement endpoints: {offenders[:5]}"


class TestInstitutionsNobodyBanksAt:
    def test_the_central_bank_is_flagged_unpayable(self):
        bb = bdbanks.bank("025")
        assert bb is not None and not bb.payable
        assert bb.payable_reason

    def test_checking_one_of_its_routings_says_why(self):
        routing = bdbanks.bank("025").branches[0].routing
        c = bdbanks.check(routing)
        assert not c
        assert any("cannot receive a salary" in p for p in c.problems)

    def test_they_are_still_looked_up_rather_than_hidden(self):
        """A lookup should answer, so a caller can explain the problem instead of
        showing 'unknown routing' for a number that plainly exists."""
        assert bdbanks.lookup(bdbanks.bank("025").branches[0].routing) is not None

    def test_payable_only_excludes_them(self):
        codes = {b.code for b in bdbanks.banks(payable_only=True)}
        assert "025" not in codes and "405" not in codes


class TestMalformedInput:
    @pytest.mark.parametrize("bad", ["", "12345", "22515013X", "2251501350", None])
    def test_it_is_reported_not_raised(self, bad):
        c = bdbanks.check(bad)
        assert not c and "not nine digits" in c.problems

    def test_an_unknown_prefix_says_so(self):
        c = bdbanks.check("999150135")
        assert not c
        assert any("belongs to no bank" in p for p in c.problems)

    def test_a_known_bank_with_an_unknown_branch_reads_differently(self):
        """'the dataset may be behind' and 'this bank does not exist' are very
        different answers to give someone."""
        c = bdbanks.check("225999999")
        assert not c
        assert any("dataset may simply be behind" in p for p in c.problems)


class TestDistrictFromTheNumberItself:
    def test_digits_four_and_five_give_the_district(self):
        assert bdbanks.district_of("225150135") == "CHATTOGRAM"

    def test_it_works_for_a_routing_not_in_the_dataset(self):
        """The point: it answers from structure, not from a lookup."""
        assert bdbanks.lookup("225159999") is None
        assert bdbanks.district_of("225159999") == "CHATTOGRAM"

    def test_malformed_gives_none(self):
        assert bdbanks.district_of("nope") is None
