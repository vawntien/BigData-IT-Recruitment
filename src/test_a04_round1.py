"""Round-1 occupational/control/provenance tests, not independent accuracy."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from a04_filter_fix_round1 import (CANDIDATE, HEADINGS, RUN, STAGES, assert_scope,
                                  checked_prediction, read_json, run_controls, stage_folder)
from it_taxonomy import Taxonomy
from tv2_csv import ROOT, sha256


class Round1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Taxonomy(CANDIDATE)
        cls.baseline = Taxonomy(RUN / "baseline/it_taxonomy_v0.2.0.json")

    def test_candidate_scope_and_frozen_baseline(self):
        assert_scope(self.model.config, STAGES)
        self.assertEqual(sha256(ROOT / "config/it_taxonomy.json"),
                         "086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d")
        self.assertEqual(self.model.version, "0.2.1")
        for key in ["decision_policy", "groups", "subgroups", "exclusion_rules"]:
            self.assertEqual(self.model.config[key], self.baseline.config[key])
        self.assertNotIn("oversee database management", self.model.config["term_sets"]["data_tasks"]["aliases"])

    def test_controls_for_baseline_and_each_individual_stage(self):
        run_controls(self.baseline, [])
        for index, stage in enumerate(STAGES, 1):
            with self.subTest(stage=stage):
                run_controls(Taxonomy(stage_folder(index, stage) / "config.json"), STAGES[:index])

    def test_explicit_heading_sections_and_blocked_evidence(self):
        for section, headings in HEADINGS.items():
            for heading in headings:
                for display in [heading.upper() + ":", heading.title()]:
                    with self.subTest(section=section, heading=display):
                        raw = "About us:\nOur company builds tools.\n" + display + "\nYou will develop software in Java."
                        p = checked_prediction(self.model, "Engineer", raw)
                        unit = next(u for u in p["description_segments"] if "You will develop" in u["text"])
                        self.assertEqual(unit["section"], section)
                        if section in {"ROLE", "RESPONSIBILITIES"}:
                            self.assertEqual(p["primary_group_code"], "SOFTWARE")
                        else:
                            self.assertEqual(p["it_decision"], "REVIEW")
                            self.assertEqual(p["match_evidence"], [])

    def test_implicit_heading_boundaries_are_not_enabled(self):
        for text in ["skillsResponsibilities: You will develop software in Java.",
                     "The OpportunityJob Description: You will develop software in Java.",
                     "Role DescriptionYou will develop software in Java.",
                     "Daily ResponsibilitiesPartner closely with engineers."]:
            raw = "About us:\nOur company builds tools.\n" + text
            old = checked_prediction(self.baseline, "Engineer", raw)
            new = checked_prediction(self.model, "Engineer", raw)
            self.assertEqual(new["it_decision"], old["it_decision"])
            self.assertFalse(any(u["section"] in {"ROLE", "RESPONSIBILITIES"} for u in new["description_segments"]))

    def test_etl_entity_mapping_and_unicode_codepoint_limit(self):
        raw = "<p>Role Description:</p><p>You will create e&#116;l pipelines using SQL.</p>"
        p = checked_prediction(self.model, "BI Analyst", raw)
        self.assertEqual(p["selected_rule_id"], "DATA_AI_CONTEXT")
        e = next(e for e in p["match_evidence"] if e["matched_alias"] == "create etl pipelines")
        self.assertIn("&#116;", "".join(raw[a:b] for a,b in e["raw_match_ranges"]))
        for length in [499, 500, 501]:
            prefix = "You will create etl pipelines using SQL "
            text = prefix + "😀" * (length-len(prefix))
            self.assertEqual(len(self.model.normalize(text)), length)
            p = checked_prediction(self.model, "BI Analyst", text)
            self.assertEqual(p["primary_group_code"], "DATA_AI")
            self.assertEqual(p["description_processing"]["incomplete"], length > 500)
            self.assertEqual(p["description_processing"]["dropped_oversize_units"], 0)

    def test_database_task_object_context_and_actor_must_cooccur(self):
        good = "Responsibilities: Oversee database management activities including data storage, retrieval, and security."
        p = checked_prediction(self.model, "Data Analyst", good)
        self.assertEqual(p["selected_rule_id"], "DATA_AI_CONTEXT")
        sets = {e["term_set_id"] for e in p["match_evidence"]}
        self.assertTrue({"database_admin_tasks", "database_admin_objects", "database_admin_context"} <= sets)
        for text in ["Oversee database management for business reporting using SQL.",
                     "Use a database for data storage, retrieval, and security.",
                     "Oversee database management. Data storage, retrieval, and security.",
                     "Qualifications: " + good.split(": ",1)[1],
                     "Help engineers who " + good.split(": ",1)[1].lower()]:
            self.assertNotEqual(checked_prediction(self.model, "Data Analyst", text)["it_decision"], "ACCEPT")

    def test_sdet_and_existing_group_subgroup_priorities(self):
        p = checked_prediction(self.model, "Software Development Engineer in Test", "")
        self.assertEqual((p["primary_group_code"], p["subgroup_code"]), ("QA_TESTING", None))
        self.assertIn("SOFTWARE_TITLE", p["matched_rule_ids"])
        self.assertIn("QA_TESTING_TITLE", p["matched_rule_ids"])
        self.assertEqual(p["selected_rule_id"], "QA_TESTING_TITLE")
        p = checked_prediction(self.model, "Founding Front-End Engineer (Web)", "You will develop mobile applications in Flutter.")
        self.assertEqual(p["subgroup_code"], "SOFTWARE_WEB")
        p = checked_prediction(self.model, "Desktop Support Technician", "Manage IT operations and lead software engineering teams.")
        self.assertEqual(p["selected_rule_id"], "IT_SUPPORT_TITLE")

    def test_identifier_has_no_effect_and_unknown_versions_fail_closed(self):
        text = "Responsibilities: You will create etl pipelines using SQL."
        a = checked_prediction(self.model, "BI Analyst", text, "101")
        b = checked_prediction(self.model, "BI Analyst", text, "999")
        self.assertEqual({k:v for k,v in a.items() if k!="job_id"}, {k:v for k,v in b.items() if k!="job_id"})
        config = copy.deepcopy(self.model.config)
        config["version"] = "0.2.3"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to((ROOT/"tmp").resolve()))
            path = Path(folder)/"unsupported.json"
            path.write_text(json.dumps(config),encoding="utf-8")
            with self.assertRaises(ValueError):
                Taxonomy(path)


if __name__ == "__main__":
    unittest.main()
