from pathlib import Path
import json
import unittest

from project_semantics.cross_domain import (
    LAWFUL_DISPOSITIONS,
    assess_case,
    run_cross_domain_pressure,
    validate_chart,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "cross_domain_cookery"
    / "bundle.json"
)


class CrossDomainCookeryPressureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_chart_is_valid(self):
        validate_chart(self.bundle["domain_chart"])

    def test_full_pressure_witness(self):
        result = run_cross_domain_pressure(self.bundle)
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["primary_disposition"], "SHARED_CORE_PLUS_LOCAL_EXTENSION"
        )
        self.assertEqual(len(result["case_results"]), 5)

    def test_all_results_are_lawful(self):
        result = run_cross_domain_pressure(self.bundle)
        self.assertTrue(
            all(
                receipt["disposition"] in LAWFUL_DISPOSITIONS
                for receipt in result["case_results"]
            )
        )

    def test_unsafe_resource_collapse_fails_closed(self):
        case = next(
            item
            for item in self.bundle["cases"]
            if item["case_id"] == "unsafe-resource-collapse"
        )
        receipt = assess_case(
            shared_core=self.bundle["shared_core"],
            chart=self.bundle["domain_chart"],
            case=case,
        )
        self.assertEqual(receipt["disposition"], "NO_SAFE_GLOBALIZATION")
        self.assertEqual(receipt["obstruction"]["kind"], "SEMANTIC_ROLE_COLLISION")

    def test_ambiguity_is_not_silently_resolved(self):
        result = run_cross_domain_pressure(self.bundle)
        dispositions = {
            item["case_id"]: item["disposition"] for item in result["case_results"]
        }
        self.assertEqual(dispositions["ambiguous-service-term"], "NON_IDENTIFIABLE")

    def test_tacit_primitive_can_force_extension(self):
        result = run_cross_domain_pressure(self.bundle)
        dispositions = {
            item["case_id"]: item["disposition"] for item in result["case_results"]
        }
        self.assertEqual(
            dispositions["tacit-aroma-grammar-gap"], "GRAMMAR_INSUFFICIENT"
        )

    def test_neutral_core_control_does_not_fail_as_software_specific(self):
        result = run_cross_domain_pressure(self.bundle)
        dispositions = {
            item["case_id"]: item["disposition"] for item in result["case_results"]
        }
        self.assertEqual(
            dispositions["software-core-pressure"],
            "SHARED_CORE_PLUS_LOCAL_EXTENSION",
        )


if __name__ == "__main__":
    unittest.main()
