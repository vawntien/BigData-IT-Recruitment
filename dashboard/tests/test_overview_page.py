"""Regression tests for Overview rendering with synthetic sample data."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))

from components import data_loader


class OverviewPageTests(unittest.TestCase):
    def setUp(self):
        # Use an absent path for production lookup; do not create data files.
        missing_analytics = DASHBOARD_DIR / "tests" / "_missing_analytics"
        self.assertFalse(missing_analytics.exists())
        production_lookup = patch.object(data_loader, "ANALYTICS_DIR", missing_analytics)
        production_lookup.start()
        self.addCleanup(production_lookup.stop)

    def load_page(self):
        return AppTest.from_file(str(DASHBOARD_DIR / "views" / "1_Overview.py")).run(timeout=20)

    def test_sample_on_renders_with_one_toggle(self):
        app = self.load_page()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.toggle), 1)
        self.assertFalse(app.toggle[0].value)
        self.assertEqual(len(app.metric), 0)
        app.toggle[0].set_value(True).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.toggle[0].value)
        self.assertTrue(any("SYNTHETIC MOCKUP DATA" in warning.value for warning in app.warning))
        self.assertEqual(len(app.metric), 4)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 4)
        self.assertEqual(
            [control.label for control in app.multiselect],
            ["Nhóm nghề", "Kinh nghiệm", "Địa điểm"],
        )
        self.assertEqual(len(app.dataframe), 1)
        self.assertTrue((app.dataframe[0].value["data_source"] == "SYNTHETIC_SAMPLE").all())

    def test_sample_off_shows_empty_state_without_error(self):
        app = self.load_page()
        app.toggle[0].set_value(True).run(timeout=20)
        app.toggle[0].set_value(False).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.toggle), 1)
        self.assertFalse(app.toggle[0].value)
        self.assertEqual(len(app.error), 0)
        self.assertTrue(any("SYNTHETIC" in item.value for item in app.markdown))
        self.assertEqual(len(app.metric), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)

    def test_no_source_lookup_before_sample_opt_in(self):
        with patch.object(data_loader, "load_overview_data", side_effect=AssertionError("unexpected lookup")) as reader:
            app = self.load_page()
        reader.assert_not_called()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
