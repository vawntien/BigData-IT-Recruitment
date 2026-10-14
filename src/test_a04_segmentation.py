"""Regression checks for the existing v0.1.0 segmentation/fallback contract.

These document current design limits; passing tests are not classifier accuracy.
"""
import unittest

from it_taxonomy import Taxonomy
from tv2_csv import ROOT


class SegmentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Taxonomy(ROOT / "config/versions/it_taxonomy_v0.1.0.json")

    def sentence_at_length(self, length):
        base = "We are seeking a software engineer to develop software in Java"
        text = base + " " + "x" * (length - len(base) - 1)
        self.assertEqual(len(self.model.normalize(text)), length)
        return text

    def test_500_unicode_codepoints_is_inclusive_not_word_or_byte_limit(self):
        allowed = self.model.classify("Specialist", self.sentence_at_length(500))
        skipped = self.model.classify("Specialist", self.sentence_at_length(501))
        self.assertEqual((allowed["it_decision"], allowed["selected_rule_id"]), ("ACCEPT", "SOFTWARE_DESCRIPTION"))
        self.assertEqual(skipped["it_decision"], "REVIEW")
        self.assertIn("DESCRIPTION_SEGMENT_SKIPPED", skipped["reason_codes"])
        emoji = "😀" * 500
        self.assertEqual(len(self.model.normalize(emoji)), 500)
        self.assertNotIn("DESCRIPTION_SEGMENT_SKIPPED", self.model.classify("Specialist", emoji)["reason_codes"])
        self.assertIn("DESCRIPTION_SEGMENT_SKIPPED", self.model.classify("Specialist", emoji + "😀")["reason_codes"])

    def test_lf_and_crlf_split_equally_before_whitespace_collapse(self):
        for separator in ["\n", "\r\n", "\n\n", "\r\n\r\n"]:
            self.assertEqual(self.model.splitter.split("first" + separator + "second"), ["first", "second"])
            description = "We are seeking a software engineer" + separator + "You will develop software in Java"
            self.assertNotEqual(self.model.classify("Specialist", description)["it_decision"], "ACCEPT")
        one_sentence = "We are seeking a software engineer; you will develop software in Java"
        # Semicolon ends a segment too; fallback cannot combine across segments.
        self.assertNotEqual(self.model.classify("Specialist", one_sentence)["it_decision"], "ACCEPT")

    def test_fallback_is_reachable_and_has_evidence_for_all_four_sets(self):
        result = self.model.classify("Specialist", "We are seeking a software engineer to develop software in Java.")
        self.assertEqual(result["selected_rule_id"], "SOFTWARE_DESCRIPTION")
        sets = {e["term_set_id"] for e in result["match_evidence"] if e["rule_id"] == "SOFTWARE_DESCRIPTION"}
        self.assertEqual(sets, {"generic_exact_titles", "software_titles", "software_tasks", "software_context", "self_role_cues"})
        named = self.model.classify("Accountant", "We are seeking a software engineer to develop software in Java.")
        self.assertNotIn("SOFTWARE_DESCRIPTION", named["matched_rule_ids"])

    def test_current_regex_keeps_html_and_cr_only_as_one_segment(self):
        html = "<p>first</p><br><p>second</p>"
        self.assertEqual(self.model.splitter.split(html), [html])
        self.assertEqual(self.model.splitter.split("first\rsecond"), ["first\rsecond"])
        self.assertEqual(self.model.normalize("first\rsecond"), "first second")

    def test_sentence_boundary_requires_following_space_and_preserves_dotnet(self):
        self.assertEqual(self.model.splitter.split("first.Second"), ["first.Second"])
        self.assertEqual(self.model.splitter.split("first.\u00a0Second"), ["first", "Second"])
        self.assertEqual(self.model.splitter.split("Use .NET and C++. Next"), ["Use .NET and C++", "Next"])

    def test_collaboration_block_is_design_even_with_valid_self_role_evidence(self):
        sentence = "We are seeking a software engineer to develop software in Java and collaborate with users"
        result = self.model.classify("Specialist", sentence)
        self.assertEqual(result["it_decision"], "REVIEW")
        self.assertNotIn("SOFTWARE_DESCRIPTION", result["matched_rule_ids"])


if __name__ == "__main__":
    unittest.main()
