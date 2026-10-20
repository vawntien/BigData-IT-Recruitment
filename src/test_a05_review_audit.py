"""Workbook reconciliation contract; never treats proposals as approved labels."""
import copy
import unittest
from audit_a05_review import reconcile


class ReviewAuditTests(unittest.TestCase):
    def setUp(self):
        self.e=dict(evidence_id="fixture",job_id="1",skill_code="PYTHON",mention_type="REQUIRED",accepted=True,
                    matched_text="Python",raw_match_ranges=[[0,6]],excerpt="Python experience")
        self.row={"evidence_id":"fixture","job_id":"1","Skill nguồn":"PYTHON","Loại nguồn":"REQUIRED","Máy nhận":True,
                  "Matched text nguồn":"Python","Raw ranges nguồn":"[[0,6]]","Quote nguyên văn":"Python experience",
                  "Quyết định đề nghị":"GIU_NHAN","Người duyệt":"","Ngày duyệt":""}

    def test_pending_workbook_matches_source_without_applying(self):
        r=reconcile([self.row],[self.e])
        self.assertEqual(r["status"],"PROPOSED_NOT_APPROVED")
        self.assertEqual(r["source_mismatches"],[])
        self.assertFalse(r["decisions_applied"])

    def test_source_change_is_reported(self):
        row=dict(self.row,**{"Skill nguồn":"JAVA"})
        self.assertEqual(reconcile([row],[self.e])["source_mismatches"][0]["field"],"Skill nguồn")

    def test_duplicate_workbook_id_rejected(self):
        with self.assertRaises(ValueError):reconcile([self.row,self.row],[self.e])

    def test_missing_source_ids_are_exposed(self):
        self.assertEqual(reconcile([],[self.e])["missing_ids"],["fixture"])

    def test_signatures_never_auto_apply_proposals(self):
        row=dict(self.row,**{"Người duyệt":"synthetic reviewer","Ngày duyệt":"2026-10-19"})
        r=reconcile([row],[self.e])
        self.assertEqual(r["status"],"REQUIRES_HUMAN_CONFIRMATION")
        self.assertFalse(r["decisions_applied"])


if __name__=="__main__":unittest.main()
