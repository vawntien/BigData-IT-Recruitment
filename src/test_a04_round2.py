"""Round-2 semantic controls, ownership boundaries and exact source evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from a04_filter_fix_round2 import (CANDIDATE, RUN, STAGES, assert_scope, checked_prediction,
                                  run_controls, stage_folder)
from it_taxonomy import Taxonomy
from tv2_csv import ROOT, sha256


class Round2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = Taxonomy(RUN / "baseline/it_taxonomy_v0.2.1.json")
        cls.model = Taxonomy(CANDIDATE)

    def test_scope_and_policy_invariants(self):
        assert_scope(self.model.config, STAGES)
        for key in ["normalization", "decision_policy", "groups", "exclusion_rules", "inputs"]:
            self.assertEqual(self.model.config[key], self.baseline.config[key])
        self.assertEqual(sha256(ROOT/"config/it_taxonomy.json"),
                         "086b0d938c7557091cb4c31f25cdfec2a746fd6853d91156087104d0f60e0d9d")
        self.assertNotIn("programmer", self.model.config["term_sets"]["software_titles"]["aliases"])

    def test_semantic_controls_at_every_stage(self):
        run_controls(self.baseline, [])
        for index, name in enumerate(STAGES, 1):
            with self.subTest(stage=name):
                run_controls(Taxonomy(stage_folder(index,name)/"config.json"), STAGES[:index])

    def test_integration_is_workflow_and_software_object_not_product_name(self):
        desc = "Role Description: Design, develop, test, and deploy integrations between software applications."
        p = checked_prediction(self.model, "Integration Engineer", desc)
        self.assertEqual((p["selected_rule_id"], p["primary_group_code"], p["subgroup_code"]),
                         ("SOFTWARE_CONTEXT", "SOFTWARE", "SOFTWARE_OTHER"))
        self.assertEqual(p["reason_codes"], ["TITLE_CONTEXT"])
        sets = {e["term_set_id"] for e in p["match_evidence"]}
        self.assertTrue({"software_integration_tasks", "software_integration_objects", "software_integration_context"} <= sets)
        for text in ["Use Workday platform for HR recruitment.",
                     "Coordinate integration in Workday platform.",
                     "Qualifications: " + desc.split(": ",1)[1],
                     "Experience to design, develop, test, and deploy integrations between software applications."]:
            self.assertNotEqual(checked_prediction(self.model, "Integration Engineer", text)["it_decision"], "ACCEPT")

    def test_migration_web_subgroup_comes_from_role_duty(self):
        duty = "This position will also migrate and upgrade selected systems from a client/server environment to a Web-based environment."
        raw = "Role Description:\n"+duty+"\nQualifications:\nDevelop applications in C#, .NET, Java, and JavaScript."
        p = checked_prediction(self.model, "Programmer", raw)
        self.assertEqual((p["selected_rule_id"],p["primary_group_code"],p["subgroup_code"]),
                         ("SOFTWARE_CONTEXT","SOFTWARE","SOFTWARE_WEB"))
        self.assertIn("SOFTWARE_WEB_CONTEXT",p["matched_rule_ids"])
        self.assertEqual(p["reason_codes"],["TITLE_CONTEXT"])
        self.assertTrue(all(e["section"]=="ROLE" for e in p["match_evidence"] if e["field"]=="description"))
        self.assertTrue(any("client/server" in e["excerpt"] for e in p["match_evidence"]))
        only_qualification = checked_prediction(self.model,"Programmer","Qualifications:\n"+duty)
        self.assertEqual(only_qualification["it_decision"],"REJECT")
        self.assertEqual(only_qualification["match_evidence"],[])

    def test_delivery_is_information_system_work_not_general_scrum(self):
        text = "Responsibilities: The Scrum Master manages all aspects of IT Epics from planning to deployment."
        p = checked_prediction(self.model,"Scrum Master",text)
        self.assertEqual((p["selected_rule_id"],p["primary_group_code"]),("IT_BUSINESS_CONTEXT","IT_BUSINESS"))
        self.assertIsNone(p["subgroup_code"])
        self.assertEqual(p["reason_codes"],["TITLE_CONTEXT"])
        for desc in ["Manages all aspects of product backlog from planning to deployment.",
                     "Manages all aspects of IT epics.",
                     "Facilitate Scrum ceremonies and product-owner meetings.",
                     "Qualifications: "+text.split(": ",1)[1]]:
            self.assertNotEqual(checked_prediction(self.model,"Scrum Master",desc)["it_decision"],"ACCEPT")

    def test_conflict_sdet_and_title_subgroup_priority_still_win(self):
        duty = "Responsibilities: Design, develop, test, and deploy integrations between software applications."
        p = checked_prediction(self.model,"Software Development Engineer in Test",duty)
        self.assertEqual(p["primary_group_code"],"QA_TESTING")
        self.assertEqual(p["selected_rule_id"],"QA_TESTING_TITLE")
        p = checked_prediction(self.model,"CNC Programmer",
            "Role Description: This position will migrate and upgrade selected systems from a client/server environment to a Web-based environment.")
        self.assertEqual(p["it_decision"],"REVIEW")
        self.assertIn("POSITIVE_EXCLUSION_CONFLICT",p["reason_codes"])
        self.assertIn("EX_PHYSICAL",p["matched_rule_ids"])
        p = checked_prediction(self.model,"Mobile Developer",
            "Role Description: You will migrate and upgrade selected systems from a client/server environment to a Web-based environment.")
        self.assertEqual(p["subgroup_code"],"SOFTWARE_MOBILE")

    def test_entity_unicode_mapping_and_task_windows(self):
        raw = "<p>Role Description:</p><p>You will migrate and upgrade selected systems from a client&#47;server environment to a Web-based environment.</p>"
        p = checked_prediction(self.model,"Programmer",raw)
        self.assertEqual(p["subgroup_code"],"SOFTWARE_WEB")
        e = next(e for e in p["match_evidence"] if e["term_set_id"]=="application_migration_origin")
        self.assertIn("&#47;","".join(raw[start:end] for start,end in e["raw_match_ranges"]))
        prefix = "You will design, develop, test, and deploy integrations between software applications "
        for length in [499,500,501]:
            desc = prefix + "😀"*(length-len(prefix))
            self.assertEqual(len(self.model.normalize(desc)),length)
            p = checked_prediction(self.model,"Integration Engineer",desc)
            self.assertEqual(p["primary_group_code"],"SOFTWARE")
            self.assertEqual(p["description_processing"]["incomplete"],length>500)
            self.assertEqual(p["description_processing"]["dropped_oversize_units"],0)

    def test_no_identifier_or_employer_override_and_fail_closed_version(self):
        duty = "Role Description: Design, develop, test, and deploy integrations between software applications."
        p1 = checked_prediction(self.model,"Integration Engineer",duty,"101")
        p2 = checked_prediction(self.model,"Integration Engineer",duty,"202")
        self.assertEqual({k:v for k,v in p1.items() if k!="job_id"},{k:v for k,v in p2.items() if k!="job_id"})
        for employer in ["Example Organization One","Example Organization Two"]:
            text = "About us:\n"+employer+" hires staff.\n"+duty
            p = checked_prediction(self.model,"Integration Engineer",text)
            self.assertEqual((p["it_decision"],p["primary_group_code"]),("ACCEPT","SOFTWARE"))
        config = copy.deepcopy(self.model.config); config["version"] = "0.2.3"
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to((ROOT/"tmp").resolve()))
            path = Path(folder)/"unsupported.json"
            path.write_text(json.dumps(config),encoding="utf-8")
            with self.assertRaises(ValueError):
                Taxonomy(path)


if __name__ == "__main__":
    unittest.main()
