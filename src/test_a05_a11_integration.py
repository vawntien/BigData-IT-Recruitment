"""Contract checks and runnable Spark fixtures; skipped runtime is never PASS."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import a06_a08_spark_analysis as analysis
import render_tv2_analysis as reports
from tv2_csv import ROOT, sha256

CONFIG = ROOT / "config/tv2_analysis_inputs.example.json"
HAS_SPARK = importlib.util.find_spec("pyspark") is not None


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_empty_contract_is_blocked_for_every_query(self):
        m = analysis.new_manifest(self.config, "test-synthetic-contract")
        self.assertEqual(m["status"], "BLOCKED_DEPENDENCY")
        self.assertEqual(len(m["queries"]), 8)
        self.assertTrue(all(q["status"] == "BLOCKED_DEPENDENCY" and q["denominator"] is None for q in m["queries"].values()))
        self.assertFalse(m["taxonomy_executed"])

    def test_pending_approval_is_not_confirmation(self):
        self.assertFalse(analysis.confirmation({"approved_by":"", "approved_on":"", "input_sha256":"x"}, {"input_sha256":"x"}))
        self.assertFalse(analysis.confirmation({"approved_by":"TV1", "approved_on":"2026-10-19", "input_sha256":"wrong"}, {"input_sha256":"actual"}))

    def test_artifact_digest_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            p = Path(folder) / "synthetic.parquet"
            p.write_bytes(b"unit-test bytes, not Parquet")
            before = analysis.artifact_digest(folder)
            p.write_bytes(b"different unit-test bytes")
            self.assertNotEqual(before, analysis.artifact_digest(folder))

    def test_d07_boolean_does_not_enable_salary(self):
        self.config["salary_d07_approved"] = True
        ready, _ = analysis.preflight(self.config)
        self.assertFalse(ready["D07"])

    def test_missing_paths_are_not_ready_even_with_reviewer(self):
        self.config.update(it_jobs="/does/not/exist", d06_confirmation={"approved_by":"fixture", "approved_on":"2026-10-19", "input_sha256":"x"})
        self.assertFalse(analysis.preflight(self.config)[0]["D06"])

    def test_dictionary_version_and_bytes_unchanged(self):
        self.assertEqual(sha256(ROOT / "config/tech_skills.json"), sha256(ROOT / "config/versions/tech_skills_v0.1.2.json"))
        self.assertEqual(json.loads((ROOT / "config/tech_skills.json").read_text(encoding="utf-8"))["version"], "0.1.2")

    def test_a05_source_namespace_matches_existing_contract(self):
        self.assertEqual(analysis.SOURCE_FIELD,"postings.description")

    def test_new_output_guard_and_persisted_blocked_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            out = Path(folder) / "new"
            self.assertEqual(analysis.main(["--contract",str(CONFIG),"--output",str(out),"--run-id","synthetic-preflight-test"]), 2)
            m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(m["environment"]["spark_executed"])
            with self.assertRaises(ValueError):
                analysis.main(["--contract",str(CONFIG),"--output",str(out),"--run-id","must-not-overwrite"])


class ReportTests(unittest.TestCase):
    def test_synthetic_success_does_not_authorize_market_results(self):
        self.assertFalse(reports.official_success({"status":"SUCCESS","run_kind":"SYNTHETIC"}))

    def test_partial_success_is_not_final_report_success(self):
        self.assertFalse(reports.official_success({"status":"PARTIAL_SUCCESS","run_kind":"OFFICIAL"}))

    def test_blocked_report_has_ten_slides_notes_and_no_results(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        m=analysis.new_manifest(config,"SYNTHETIC_REPORT_CONTRACT_TEST")
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as folder:
            source=Path(folder)/"manifest.json"
            source.write_text(json.dumps(m),encoding="utf-8")
            out=Path(folder)/"reports"
            reports.render(source,out)
            document=(out/"a11_slides.html").read_text(encoding="utf-8")
            self.assertEqual(document.count('<section class="slide"'),10)
            self.assertEqual(document.count('<details open>'),10)
            self.assertGreaterEqual(document.count('<svg'),3)
            publication=json.loads((out/"publication_manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(publication["market_results_published"])
            self.assertIn("CHỜ INPUT",(out/"a09_insights.md").read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):reports.render(source,out)

    def test_modified_csv_blocks_official_publication(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as folder:
            p=Path(folder)/"table.csv";p.write_text("category,job_count\nX,1\n",encoding="utf-8")
            m=dict(status="SUCCESS",run_kind="OFFICIAL",dependencies={k:True for k in ["D05","D06","A05","D07"]},
                   queries={f"Q{i:02d}":dict(status="SUCCESS") for i in range(1,9)},tables={"fixture":dict(csv="table.csv",csv_sha256="wrong")})
            with self.assertRaises(ValueError):reports.read_tables(Path(folder),m)

    def test_waiting_insights_do_not_use_supplied_fake_counts(self):
        values=reports.insights({"status":"BLOCKED_DEPENDENCY"},{"q01_role_groups":[{"category":"fabricated","job_count":"999999"}]})
        self.assertEqual(len(values),8)
        self.assertFalse(any("999999" in value for value in values))


@unittest.skipUnless(HAS_SPARK, "SKIP: PySpark absent; Java 21 / Spark runtime required")
class SparkSyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        info = analysis.runtime()
        import re
        match = re.search(r'"(\d+)', info["java"])
        if not match or int(match.group(1)) < 21:
            raise unittest.SkipTest("SKIP: Java 21 required by repository runtime")
        analysis.load_spark()
        from pyspark.sql import SparkSession
        cls.spark = SparkSession.builder.master("local[2]").appName("TV2-A05-A11-SYNTHETIC").getOrCreate()
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.conf.set("spark.sql.shuffle.partitions", "2")
        schema = "job_id long, description string, it_decision string, is_it boolean, taxonomy_version string, taxonomy_sha256 string, primary_group_code string, formatted_experience_level string, location string, formatted_work_type string, work_type string, remote_allowed boolean, original_listed_time timestamp, listed_time timestamp"
        cls.rows = [(1,"Requirements: Python programming experience.","ACCEPT",True,"synthetic","fixture","SOFTWARE","Entry level","A","Full-time","FULL_TIME",True,datetime(2024,1,1),datetime(2024,1,3)),
                    (2,"Maintain office records.","ACCEPT",True,"synthetic","fixture","SOFTWARE",None,None,"Full-time","FULL_TIME",None,datetime(2024,1,2),None),
                    (3,None,"ACCEPT",True,"synthetic","fixture","DATA_AI","Senior","B","Part-time","PART_TIME",False,None,datetime(2024,1,4))]
        cls.d = cls.spark.createDataFrame(cls.rows, schema)
        from a05_spark import extract_frames
        cls.frames, cls.cache, cls.n = extract_frames(cls.d,ROOT / "config/tech_skills.json","SYNTHETIC_PARITY_ONLY")
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.cache.unpersist()
        cls.spark.stop()

    def test_a05_distributed_parity_with_existing_extractor(self):
        from a05_spark import spark_record
        from tech_skill_extractor import TechSkillExtractor
        model = TechSkillExtractor(ROOT / "config/tech_skills.json")
        results = [model.extract(row[1],row[0],run_id="SYNTHETIC_PARITY_ONLY") for row in self.rows]
        def canonical(rows):
            return sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows)
        for table, key in [("job_skill_technical","job_skills"),("technical_skill_evidence","evidence")]:
            self.assertEqual(canonical([r.asDict(recursive=True) for r in self.frames[table].collect()]), canonical([spark_record(x) for result in results for x in result[key]]))
        self.assertEqual(canonical([r.asDict(recursive=True) for r in self.frames["skill_source_processing"].collect()]),canonical([spark_record(r["processing"]) for r in results]))

    def test_a05_synthetic_parquet_readback(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for name, table in self.frames.items():
                path = str(Path(folder) / (name + ".parquet"))
                table.write.mode("errorifexists").parquet(path)
                saved = self.spark.read.parquet(path)
                self.assertEqual(saved.count(),table.count())
                self.assertEqual(table.exceptAll(saved.select(table.columns)).count(),0)

    def test_q06_denominator_includes_successful_zero_hit(self):
        tables, meta, n = analysis.analyze_frames(self.d,self.config,bridge=self.frames["job_skill_technical"],proc=self.frames["skill_source_processing"])
        self.assertEqual(n,3)
        self.assertEqual(meta["Q06"]["denominator"],2)
        self.assertEqual(meta["Q06"]["zero_hit_jobs"],1)
        python = tables["q06_skills_global"].filter("skill_code = 'PYTHON'").first()
        self.assertEqual(python["job_count"],1)
        self.assertAlmostEqual(python["share_of_processed"],0.5)
        self.assertEqual(sum(r["job_count"] for r in tables["q01_role_groups"].collect()),3)

    def test_duplicate_grain_rejected(self):
        with self.assertRaises(ValueError):
            analysis.analyze_frames(self.d.unionByName(self.d.limit(1)),self.config)

    def test_q05_multilabel_does_not_multiply_base(self):
        js = self.spark.createDataFrame([(1,"IT"),(1,"ENG"),(1,"IT"),(999,"IT")],"job_id long, skill_abr string")
        sk = self.spark.createDataFrame([("IT","Information Technology"),("ENG","Engineering")],"skill_abr string, skill_name string")
        tables, meta, n = analysis.analyze_frames(self.d,self.config,js=js,sk=sk)
        self.assertEqual(n,3)
        self.assertEqual(meta["Q05"]["denominator"],1)
        self.assertEqual(sum(r["job_count"] for r in tables["q05_functional_labels"].collect()),2)

    def test_salary_currency_period_source_are_separate(self):
        from test_q07_salary import fixture
        population, salary = fixture(self.spark)
        from q07_salary import salary_tables
        table = salary_tables(population, salary, scope_id="SYNTHETIC_NOT_IT")["q07_salary_separate_units"]
        self.assertEqual(table.count(),5)
        self.assertTrue(all(r["adequate_min"] is None for r in table.collect()))



@unittest.skipUnless(HAS_SPARK and os.environ.get("TV2_OFFICIAL_CONTRACT"), "SKIP: no TV1-confirmed D06 contract/runtime; never substitute 105 development jobs")
class SparkRealTests(unittest.TestCase):
    def test_confirmed_d06_end_to_end(self):
        contract = Path(os.environ["TV2_OFFICIAL_CONTRACT"])
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            out = Path(folder) / "real-integration-new-output"
            code = analysis.main(["--contract",str(contract),"--output",str(out),"--run-id","TV1_CONFIRMED_REAL_TEST"])
            m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn(code,[0,2])
            self.assertIn(m["status"],["SUCCESS","PARTIAL_SUCCESS"])
            self.assertEqual(m["queries"]["Q01"]["status"],"SUCCESS")


if __name__ == "__main__":
    unittest.main()
