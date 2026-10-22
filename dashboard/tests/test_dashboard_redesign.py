"""UI-only coverage of native navigation and isolated sample presentation."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from streamlit.runtime.pages_manager import PagesManager
from streamlit.util import calc_md5
DASHBOARD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD))
from components import data_loader as dl, q01_real_preview as real


class RedesignTests(unittest.TestCase):
    def setUp(self):
        # Compatibility for native Page.run in Streamlit 1.38 AppTest only.
        patcher = patch.object(PagesManager, "get_page_script_byte_code",
            lambda _, path: compile(Path(path).read_text(encoding="utf-8"), str(path), "exec"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def page(self, name):
        app = AppTest.from_file(str(DASHBOARD / "views" / name)).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        return app

    def test_home_has_navigation_without_implicit_read(self):
        with patch.object(pd, "read_csv") as csv, patch.object(pd, "read_parquet") as parquet, patch.object(real, "load_q01_preview") as preview:
            app = AppTest.from_file(str(DASHBOARD / "app.py")).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "IT Recruitment Analytics")
        self.assertEqual(len(app.metric), 0)
        self.assertGreaterEqual(len(app.get("page_link")), 5)
        for reader in (csv, parquet, preview):
            reader.assert_not_called()

    def test_all_native_routes_render(self):
        app = AppTest.from_file(str(DASHBOARD / "app.py")).run(timeout=20)
        for route in ["Data_Quality", "Skills", "Salary_Quality", "Overview", "Demo_Analytics", "Q01_Synthetic_Demo", "Q01_Real_Preview"]:
            app._page_hash = calc_md5(route)
            app.run(timeout=20)
            self.assertEqual(len(app.exception), 0, route)
            self.assertEqual(len(app.title), 1, route)

    def test_official_skills_salary_have_no_sample_results(self):
        with patch.object(dl, "load_skills_data") as skills, patch.object(dl, "load_salary_quality_data") as salary:
            for name in ["2_Skills.py", "3_Salary_Quality.py"]:
                app = self.page(name)
                self.assertEqual(len(app.toggle), 0)
                self.assertEqual(len(app.metric), 0)
                self.assertEqual(len(app.dataframe), 0)
        skills.assert_not_called()
        salary.assert_not_called()

    def test_demo_requires_opt_in_per_view(self):
        with patch.object(dl, "load_skills_data") as skills, patch.object(dl, "load_salary_quality_data") as salary:
            app = self.page("7_Demo_Analytics.py")
            self.assertEqual([tab.label for tab in app.tabs], ["Kỹ năng", "Thu nhập"])
        skills.assert_not_called()
        salary.assert_not_called()
        self.assertFalse(app.toggle[0].value)
        self.assertEqual(len(app.dataframe), 0)

    def test_demo_tabs_do_not_transfer_consent(self):
        with patch.object(dl, "load_skills_data", wraps=dl.load_skills_data) as skills, patch.object(dl, "load_salary_quality_data", wraps=dl.load_salary_quality_data) as salary:
            app = self.page("7_Demo_Analytics.py")
            self.assertEqual(len(app.toggle), 2)
            app.toggle[0].set_value(True).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            skills.assert_called_once_with(enable_sample_mode=True)
            salary.assert_not_called()
            self.assertIs(app.toggle[1].value, False)
            self.assertEqual(len(app.dataframe), 2)
            app.toggle[0].set_value(False).run(timeout=20)
            app.toggle[1].set_value(True).run(timeout=20)
            self.assertIs(app.toggle[0].value, False)
            self.assertEqual(len(app.dataframe), 1)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(skills.call_count, 1)
            salary.assert_called_once_with(enable_sample_mode=True)

    def test_skill_tables_preserved_and_off_clears(self):
        app = self.page("7_Demo_Analytics.py")
        app.toggle[0].set_value(True).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.dataframe), 2)
        self.assertIn("frequency_pct", app.dataframe[0].value.columns)
        self.assertIn("technical_skill", app.dataframe[1].value.columns)
        app.toggle[0].set_value(False).run(timeout=20)
        self.assertEqual(len(app.dataframe), 0)
        self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)

    def test_salary_units_are_not_mixed(self):
        app = self.page("7_Demo_Analytics.py")
        app.toggle[1].set_value(True).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        table = app.dataframe[0].value
        self.assertEqual(table.currency.nunique(), 1)
        self.assertEqual(table.pay_period.nunique(), 1)
        self.assertEqual(table.currency.iloc[0], app.selectbox[0].value)
        self.assertEqual(table.pay_period.iloc[0], app.selectbox[1].value)

    def test_overview_empty_filters_mean_all_and_filter_changes_count(self):
        app = self.page("1_Overview.py")
        app.toggle[0].set_value(True).run(timeout=20)
        self.assertTrue(all(control.value == [] for control in app.multiselect))
        total = app.metric[0].value
        app.multiselect[0].set_value([app.multiselect[0].options[0]]).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertNotEqual(app.metric[0].value, total)
        app.multiselect[0].set_value([]).run(timeout=20)
        self.assertEqual(app.metric[0].value, total)

    def test_historical_quality_is_scoped_and_separate(self):
        app = self.page("6_Data_Quality.py")
        text = " ".join(str(m.value) for m in app.markdown)
        self.assertIn("HISTORICAL RAW/CLEAN", text)
        self.assertIn("ALL JOBS", text)
        self.assertIn("không phải accepted IT production", text)
        self.assertEqual(app.metric[0].value, "123,849")
        self.assertEqual(len(app.selectbox), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
