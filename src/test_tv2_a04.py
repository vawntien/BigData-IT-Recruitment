"""Contract checks for taxonomy interpretation, evidence, CSV, and sampling."""
import json
import random
import tempfile
import unittest
from pathlib import Path

from it_taxonomy import Taxonomy
from prepare_a04 import MANUAL_FIELDS, STRATA, choose_sample, stratum
from tv2_csv import ROOT, csv_rows, integer_key, write_csv


class A04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Taxonomy(ROOT / "config/versions/it_taxonomy_v0.1.0.json")

    def test_all_57_design_cases(self):
        self.assertEqual(self.model.check_illustrative_cases(), 57)

    def test_conflict_has_both_sides_and_no_primary(self):
        result = self.model.classify("Financial Analyst / Software Engineer", "Develop software in Java.", "123.0")
        self.assertEqual((result["job_id"], result["it_decision"], result["is_it"], result["primary_group_code"]), ("123", "REVIEW", None, None))
        self.assertIn("SOFTWARE_TITLE", result["matched_rule_ids"])
        self.assertIn("EX_COMMERCIAL", result["matched_rule_ids"])
        self.assertTrue(all(e["excerpt"] for e in result["match_evidence"]))

    def test_evidence_is_real_source_near_late_hit(self):
        title = "prefix " * 60 + "Software—Engineer"
        result = self.model.classify(title, "")
        evidence = next(e for e in result["match_evidence"] if e["rule_id"] == "SOFTWARE_TITLE")
        self.assertIn("Software—Engineer", evidence["excerpt"])
        self.assertIn(evidence["excerpt"], title)
        self.assertLessEqual(len(evidence["excerpt"]), 240)
        decomposed = "Ky\u0303 sư phâ\u0300n mê\u0300m"
        self.assertEqual(self.model.classify(decomposed, None)["primary_group_code"], "SOFTWARE")

    def test_no_cross_segment_or_company_evidence(self):
        for description in ["Write production code. Java.", "Our company develops software in Java.", "Not responsible for developing software in Java."]:
            result = self.model.classify("Developer", description)
            self.assertNotEqual(result["it_decision"], "ACCEPT")
        long_segment = "x " * 260 + "develop software in Java"
        result = self.model.classify("Developer", long_segment)
        self.assertEqual(result["it_decision"], "REVIEW")
        self.assertIn("DESCRIPTION_SEGMENT_SKIPPED", result["reason_codes"])

    def test_group_priority_does_not_depend_on_array_order(self):
        config = json.loads((ROOT / "config/versions/it_taxonomy_v0.1.0.json").read_text(encoding="utf-8"))
        config["include_rules"].reverse()
        config["groups"].reverse()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            other = Taxonomy(path)
            title = "Software Engineer / Data Engineer"
            for model in [self.model, other]:
                result = model.classify(title, None)
                self.assertEqual(result["primary_group_code"], "DATA_AI")
                self.assertEqual(result["candidate_group_codes"], ["DATA_AI", "SOFTWARE"])

    def test_invalid_config_fails_closed(self):
        config = json.loads((ROOT / "config/versions/it_taxonomy_v0.1.0.json").read_text(encoding="utf-8"))
        config["include_rules"][0]["condition"] = {"all": []}
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(ValueError):
                Taxonomy(path)

    def test_csv_multiline_and_no_overwrite(self):
        row = dict(job_id="123", title='Quoted, "title"', description="line one\nline two, comma\n" + "x" * 40000, **{k: "" for k in MANUAL_FIELDS})
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "labels.csv"
            write_csv(path, [row], list(row), exclusive=True, bom=True)
            self.assertEqual(list(csv_rows(path)), [row])
            with self.assertRaises(FileExistsError):
                write_csv(path, [row], list(row), exclusive=True)
        self.assertEqual(integer_key("123.000"), "123")
        with self.assertRaises(ValueError):
            integer_key("123.5")

    def test_sampling_disjoint_reproducible_and_quotas(self):
        records = []
        for s in range(5):
            for i in range(100):
                r = dict(job_id=str(s * 100 + i + 1), title="example", it_decision=["ACCEPT", "ACCEPT", "REJECT", "REJECT", "REVIEW"][s], primary_group_code="SOFTWARE" if s < 2 else None, subgroup_code="SOFTWARE_WEB" if s == 1 else None, candidate_group_codes=["SOFTWARE"] if s < 2 else [], matched_rule_ids=["EX_COMMERCIAL"] if s == 2 else [], reason_codes=["OUTSIDE_IT_ROLE"] if s == 2 else [])
                self.assertEqual(stratum(r), STRATA[s])
                records.append(r)
        sample, design = choose_sample(records, self.model, set())
        shuffled = records.copy()
        random.Random(999).shuffle(shuffled)
        sample2, _ = choose_sample(shuffled, self.model, set())
        self.assertEqual([r["job_id"] for r in sample], [r["job_id"] for r in sample2])
        self.assertEqual(len({r["job_id"] for r in sample}), 160)
        self.assertEqual(design["sample_counts"], dict(zip(STRATA, [50, 30, 30, 20, 30])))


if __name__ == "__main__":
    unittest.main()
