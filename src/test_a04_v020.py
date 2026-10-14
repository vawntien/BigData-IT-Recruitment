"""v0.2 behavior/provenance tests, not occupational gold labels or accuracy."""
import json
import unittest

from description_processing import normalized_spans
from it_taxonomy import Taxonomy
from tv2_csv import ROOT, sha256


class StructuredDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Taxonomy(ROOT / "config/it_taxonomy.json")
        cls.old = Taxonomy(ROOT / "config/versions/it_taxonomy_v0.1.0.json")

    def classify(self, text, title="Engineer"):
        return self.model.classify(title, text)

    def test_version_snapshot_and_occupation_invariants(self):
        self.assertEqual(sha256(ROOT / "config/versions/it_taxonomy_v0.1.0.json"), "99523fff775fc302507638b532491275c3bec54d2d38354ce329f574943c8278")
        self.assertEqual(sha256(ROOT / "src/it_taxonomy_v010.py"), "453bb6bcd22d4cdf866c670f3634b8f1e42a233eb086b650e579b4b1d429dc86")
        for key in ["groups", "subgroups", "term_sets", "include_rules", "general_it_rules", "exclusion_rules", "a04_review_design"]:
            self.assertEqual(self.model.config[key], self.old.config[key], key)
        self.assertEqual(self.model.check_illustrative_cases(), 57)
        self.assertEqual(self.old.check_illustrative_cases(), 57)

    def test_long_tasks_are_retained_and_local_owned_evidence_is_used(self):
        text = "We are seeking a software engineer to develop software in Java " + "detail " * 100
        before = self.old.classify("Specialist", text)
        after = self.classify(text, "Specialist")
        self.assertIn("DESCRIPTION_SEGMENT_SKIPPED", before["reason_codes"])
        self.assertEqual(after["selected_rule_id"], "SOFTWARE_DESCRIPTION")
        self.assertEqual(after["description_segments"][0]["text"], text)
        self.assertEqual(after["description_processing"]["dropped_oversize_units"], 0)
        self.assertTrue(after["description_processing"]["incomplete"])

    def test_long_source_resolved_into_sentences_does_not_force_review(self):
        text = ("Prepare reports for clients. " * 30) + "You will develop software in Java."
        result = self.classify(text)
        self.assertEqual(result["it_decision"], "ACCEPT")
        self.assertFalse(result["description_processing"]["incomplete"])
        self.assertNotIn("DESCRIPTION_PROCESSING_INCOMPLETE", result["reason_codes"])

    def test_residual_long_unknown_content_is_visible_and_explicit(self):
        text = "opaque " * 150
        result = self.classify(text, "Unmapped position")
        self.assertEqual(result["it_decision"], "REVIEW")
        self.assertIn("DESCRIPTION_PROCESSING_INCOMPLETE", result["reason_codes"])
        self.assertEqual(result["description_segments"][0]["text"], text)

    def test_collaboration_does_not_cancel_owned_task(self):
        for text in ["Develop software in Java and collaborate with users.",
                     "You will collaborate with architects to develop software in Java.",
                     "Develop software in Java and work with customers."]:
            with self.subTest(text=text):
                self.assertIn("SOFTWARE_CONTEXT", self.classify(text)["matched_rule_ids"])

    def test_collaboration_only_and_other_team_task_are_not_self_tasks(self):
        for text in ["Work with a team to develop software in Java.",
                     "Help project teams build applications in Java.",
                     "You will collaborate with engineers who develop software in Java.",
                     "Collaborate with a software team using Java."]:
            with self.subTest(text=text):
                self.assertNotIn("SOFTWARE_CONTEXT", self.classify(text)["matched_rule_ids"])

    def test_negation_is_kept_but_adversative_clauses_are_separate(self):
        self.assertNotIn("SOFTWARE_CONTEXT", self.classify("Do not develop software in Java.")["matched_rule_ids"])
        result = self.classify("You are not responsible for sales, but you will develop software in Java.")
        self.assertIn("SOFTWARE_CONTEXT", result["matched_rule_ids"])
        long_negation = "You will not be responsible for " + "details " * 100 + "develop software in Java"
        # Use the actual configured negation alias, not an invented synonym.
        long_negation = long_negation.replace("not be responsible", "not responsible")
        self.assertNotIn("SOFTWARE_CONTEXT", self.classify(long_negation)["matched_rule_ids"])

    def test_company_qualifications_and_compensation_do_not_supply_tasks(self):
        for text in ["Our company builds software. Our clients develop software in Java.",
                     "We are an engineering team that will develop software in Java.",
                     "About us: We develop software in Java.",
                     "Qualifications: Experience to develop software in Java.",
                     "Compensation: You will develop software in Java.",
                     "Benefits: We are seeking a software engineer to develop software in Java."]:
            with self.subTest(text=text):
                self.assertNotIn("SOFTWARE_CONTEXT", self.classify(text)["matched_rule_ids"])

    def test_no_cross_salary_benefit_or_sentence_gluing(self):
        for text in ["Responsibilities: Write production code. Compensation: Java.",
                     "Responsibilities: Write production code. Benefits: Java.",
                     "Responsibilities: Write production code. Java."]:
            self.assertNotIn("SOFTWARE_CONTEXT", self.classify(text)["matched_rule_ids"])
        text = "Responsibilities: A software engineer must write production code. Compensation: This role uses Java."
        self.assertNotIn("SOFTWARE_DESCRIPTION", self.classify(text, "Specialist")["matched_rule_ids"])

    def test_heading_reset_allows_actual_responsibilities_after_company(self):
        text = "About us:\nWe develop software in Java.\nResponsibilities:\nYou will develop software in Java.\nBenefits:\nJava classes."
        result = self.classify(text)
        self.assertIn("SOFTWARE_CONTEXT", result["matched_rule_ids"])
        self.assertTrue(all(e["section"] == "RESPONSIBILITIES" for e in result["match_evidence"] if e["field"] == "description"))

    def test_html_lists_entities_and_script_style_suppression(self):
        text = '<style>.x { develop software in Java; }</style><script>develop software in Java</script><p>Responsibilities:</p><ul><li>You will develop <b>software</b> in Java &amp; .NET 6.0.</li></ul>'
        result = self.classify(text)
        self.assertIn("SOFTWARE_CONTEXT", result["matched_rule_ids"])
        visible = " ".join(u["text"] for u in result["description_segments"])
        self.assertNotIn(".x", visible)
        self.assertNotIn("<b>", visible)
        self.assertIn("Java & .NET 6.0", visible)
        self.assertEqual(len(result["description_processing"]["removed_source_ranges"]), 2)
        self.assertNotIn("SOFTWARE_CONTEXT", self.classify("<script>develop software in Java</script>")["matched_rule_ids"])
        for evidence in result["match_evidence"]:
            source = text if evidence["field"] == "description" else "Engineer"
            self.assertEqual(evidence["excerpt"], source[evidence["raw_excerpt_start"]:evidence["raw_excerpt_end"]])
            self.assertEqual(evidence["mapping_status"], "MAPPED_TO_RAW")
            self.assertTrue(evidence["raw_match_ranges"])

    def test_dotnet_urls_versions_abbreviations_and_bullets(self):
        text = "You will develop software in .NET 6.0 at https://example.org/v1.2/api. Reference U.S. standards.·You will build applications in Java."
        result = self.classify(text)
        units = [u["text"] for u in result["description_segments"]]
        self.assertTrue(any(".NET 6.0" in u and "https://example.org/v1.2/api." in u for u in units))
        self.assertTrue(any("U.S." in u for u in units))
        self.assertTrue(any(u.strip() == "You will build applications in Java" for u in units))
        self.assertEqual(result["it_decision"], "ACCEPT")

    def test_all_newline_forms_and_numbered_bullets(self):
        for separator in ["\n", "\r\n", "\r", "\u2028", "\u2029"]:
            r = self.classify("First task" + separator + "You will develop software in Java")
            self.assertEqual(len(r["description_segments"]), 2)
        r = self.classify("1. You will develop software in Java\n2. Prepare reports")
        self.assertIn("SOFTWARE_CONTEXT", r["matched_rule_ids"])

    def test_normalization_and_entity_source_mapping(self):
        raw = '<p>You will develop soft&#119;are in Java &amp; .NET.</p>'
        result = self.classify(raw)
        hit = next(e for e in result["match_evidence"] if e["matched_alias"] == "develop software")
        self.assertEqual(hit["derived_matched_text"], "develop software")
        self.assertIn("&#119;", "".join(raw[a:b] for a, b in hit["raw_match_ranges"]))
        original = "Ky\u0303 sư phâ\u0300n mê\u0300m"
        value, spans = normalized_spans(self.model, original)
        self.assertEqual(value, self.model.normalize(original))
        self.assertEqual((spans[0][0], spans[-1][1]), (0, len(original)))
        self.assertEqual(self.classify("", original)["primary_group_code"], "SOFTWARE")

    def test_health_sales_tools_and_positive_exclusion_conflicts(self):
        for title in ["Registered Nurse", "Account Manager"]:
            result = self.classify("Use SQL reports and company software to serve customers.", title)
            self.assertEqual(result["it_decision"], "REJECT")
        result = self.classify("You will develop software in Java.", "Sales Engineer")
        self.assertEqual(result["it_decision"], "REVIEW")
        self.assertIn("POSITIVE_EXCLUSION_CONFLICT", result["reason_codes"])

    def test_real_diagnostic_cases_are_sources_not_gold_labels(self):
        folder = ROOT / "data/analytics/a04_diagnostics_v0_1_0_20261008"
        rows = json.loads((folder / "real_job_specimens.json").read_text(encoding="utf-8"))
        rows += json.loads((folder / "description_gate_task_examples.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 20)
        for row in rows:
            old = self.old.classify(row["title"], row["description"], row["job_id"])
            self.assertTrue(all(old[k] == v for k, v in row["original_prediction"].items()))
            result = self.model.classify(row["title"], row["description"], row["job_id"])
            self.assertEqual(result["description_processing"]["dropped_oversize_units"], 0)
            for e in result["match_evidence"]:
                source = row[e["field"]]
                self.assertEqual(e["excerpt"], source[e["raw_excerpt_start"]:e["raw_excerpt_end"]])
                self.assertTrue(all(0 <= a < b <= len(source) for a, b in e["raw_match_ranges"]))
            if row["job_id"] in ["3902916761", "3895536438", "3894268653"]:
                # Check configured exclusions persist; this is not a manual label.
                self.assertTrue(set(old["matched_rule_ids"]) & set(result["matched_rule_ids"]))


if __name__ == "__main__":
    unittest.main()
