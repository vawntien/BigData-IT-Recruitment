"""Synthetic D09 validator regression only; not real-artifact evidence."""
import copy
import statistics
import unittest
from d09_validate_available import Audit, STATES, safe_member, tally, verify_statistics


def fixture():
    rows, summaries = [], []
    for workload in ('W1', 'W2', 'W3', 'W4', 'W5'):
        for master, factor in [('local[1]', 1), ('local[2]', 2), ('local[4]', 4)]:
            for phase, repeat, seconds in [('warmup', 0, 999), ('measured', 1, 3/factor),
                                           ('measured', 2, 1/factor), ('measured', 3, 2/factor)]:
                rows.append(dict(workload=workload, master=master, phase=phase, repeat=str(repeat),
                                 elapsed_seconds=str(seconds), correctness='PASS', result_json='{}'))
            summaries.append(dict(workload=workload, master=master, samples='3', min_seconds=1/factor,
                                  median_seconds=2/factor, max_seconds=3/factor, speedup_vs_local1=factor))
    return rows, summaries


class ValidationTests(unittest.TestCase):
    def test_measured_only_statistics(self):
        rows, summaries = fixture()
        self.assertEqual(verify_statistics(rows, summaries)['measured'], 45)

    def test_wrong_median_and_speedup_rejected(self):
        rows, summaries = fixture()
        for field in ('median_seconds', 'speedup_vs_local1', 'min_seconds', 'max_seconds'):
            bad = copy.deepcopy(summaries); bad[0][field] = 77
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_statistics(rows, bad)

    def test_missing_duplicate_repeat_rejected(self):
        rows, summaries = fixture(); rows[1]['repeat'] = '2'
        with self.assertRaises(ValueError): verify_statistics(rows, summaries)
        rows, summaries = fixture(); rows.pop()
        with self.assertRaises(ValueError): verify_statistics(rows, summaries)

    def test_nan_and_cross_config_result_rejected(self):
        rows, summaries = fixture(); rows[1]['elapsed_seconds'] = 'nan'
        with self.assertRaises(ValueError): verify_statistics(rows, summaries)
        rows, summaries = fixture(); rows[1]['result_json'] = '{"tampered":true}'
        with self.assertRaises(ValueError): verify_statistics(rows, summaries)

    def test_all_four_states_are_counted(self):
        records = [{'status': s} for s in STATES]
        counts = tally(records)
        self.assertEqual(counts, {'TOTAL': 4, 'PASS': 1, 'FAIL': 1, 'BLOCKED': 1, 'NOT APPLICABLE': 1})
        with self.assertRaises(ValueError): tally([{'status': 'PENDING'}])

    def test_failed_check_is_not_pass(self):
        audit = Audit(); audit.check('bad', lambda: 1/0)
        self.assertEqual(audit.records[0]['status'], 'FAIL')
        with self.assertRaises(ValueError): audit.record('bad', 'PASS', {})

    def test_archive_paths_no_traversal(self):
        self.assertEqual(str(safe_member('D05/jobs/part.parquet')), 'D05/jobs/part.parquet')
        for path in ('../private', '/absolute', 'D:/absolute', 'D05\\..\\private'):
            with self.subTest(path=path), self.assertRaises(ValueError): safe_member(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
