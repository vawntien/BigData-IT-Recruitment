"""A05 semantic fixtures; they are not occupational/skill gold labels."""
import copy
import hashlib
import json
import csv
import tempfile
import unittest
from pathlib import Path

from tech_skill_extractor import TechSkillExtractor
from tv2_csv import ROOT


class SkillExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = TechSkillExtractor(ROOT / "config/tech_skills.json")

    def extract(self, text, job="101"):
        return self.model.extract(text, job, run_id="test")

    def codes(self, text):
        return {x["skill_code"] for x in self.extract(text)["job_skills"]}

    def test_java_is_not_javascript(self):
        self.assertEqual(self.codes("Qualifications: Experience with JavaScript."), {"JAVASCRIPT"})
        self.assertEqual(self.codes("Qualifications: Experience with Java and JavaScript."), {"JAVA", "JAVASCRIPT"})

    def test_c_variants_and_runtimes_are_distinct(self):
        text = "Requirements: C++, C#, C programming language, .NET and Node.js."
        self.assertEqual(self.codes(text), {"CPP", "CSHARP", "C", "DOTNET", "NODEJS"})
        self.assertEqual(self.codes("Requirements: C++ and C#."), {"CPP", "CSHARP"})

    def test_longest_database_alias_without_inferred_sql(self):
        self.assertEqual(self.codes("Responsibilities: Use Microsoft SQL Server."), {"SQL_SERVER"})
        self.assertEqual(self.codes("Responsibilities: Use SQL Server and SQL."), {"SQL_SERVER", "SQL"})
        self.assertEqual(self.codes("Responsibilities: Use MySQL and PostgreSQL."), {"MYSQL", "POSTGRESQL"})

    def test_longest_framework_alias(self):
        self.assertEqual(self.codes("Requirements: Experience with ASP.NET Core."), {"ASPNET"})
        self.assertEqual(self.codes("Requirements: Experience with .NET Core and ASP.NET."), {"DOTNET", "ASPNET"})

    def test_go_r_c_need_technical_context(self):
        self.assertEqual(self.codes("Qualifications: Programming languages: Python, Go and R."), {"PYTHON", "GO", "R"})
        self.assertEqual(self.codes("Qualifications: C/C++, Golang and R programming language."), {"C", "CPP", "GO", "R"})
        self.assertFalse(self.codes("Qualifications: Go to the office. Grade C. Vitamin C. R&D."))

    def test_ambiguous_words_do_not_validate_each_other(self):
        result = self.extract("Requirements: Go or R.")
        self.assertFalse(result["job_skills"])
        self.assertEqual(result["processing"]["ambiguous_evidence_count"], 2)
        self.assertTrue(result["processing"]["review_required"])

    def test_spark_react_spring_and_swift_context(self):
        self.assertEqual(self.codes("Requirements: Java Spring framework, Apache Spark, iOS Swift programming language, ReactJS."),
                         {"JAVA", "SPRING", "SPARK", "SWIFT", "REACT"})
        self.assertFalse(self.codes("Qualifications: Spark joy. React to events. Spring season. Swift responses."))

    def test_qualifications_are_eligible(self):
        r = self.extract("About us:\nOur company uses Ruby.\nQualifications:\nExperience with Python and SQL.")
        self.assertEqual({x["skill_code"] for x in r["job_skills"]}, {"PYTHON", "SQL"})
        self.assertTrue(all(e["mention_type"] == "REQUIRED" for e in r["evidence"] if e["accepted"]))

    def test_required_preferred_and_tasks_are_separate(self):
        r = self.extract("Qualifications:\nPython required, Java preferred.\nResponsibilities:\nDeploy Docker.\nPreferred Skills:\nKubernetes.")
        by_code = {x["skill_code"]: x["mention_types"] for x in r["job_skills"]}
        self.assertEqual(by_code, {"PYTHON": ["REQUIRED"], "JAVA": ["PREFERRED"], "DOCKER": ["TASK"], "KUBERNETES": ["PREFERRED"]})

    def test_company_only_mentions_are_preserved_but_not_counted(self):
        r = self.extract("About us:\nWe build Python products using AWS.\nResponsibilities:\nYou will develop Java services.")
        self.assertEqual({x["skill_code"] for x in r["job_skills"]}, {"JAVA"})
        self.assertEqual({e["skill_code"] for e in r["evidence"] if e["mention_type"] == "COMPANY_ONLY"}, {"PYTHON", "AWS"})

    def test_company_subject_without_heading(self):
        self.assertFalse(self.codes("We use Python to provide services to our customers."))
        self.assertEqual(self.codes("We are looking for a candidate with Python experience."), {"PYTHON"})

    def test_unknown_scope_is_review_not_requirement(self):
        r = self.extract("Python, Java, AWS.")
        self.assertFalse(r["job_skills"])
        self.assertTrue(all(e["mention_type"] == "AMBIGUOUS_SCOPE" for e in r["evidence"]))

    def test_negated_requirement_does_not_become_skill(self):
        self.assertFalse(self.codes("Qualifications: No experience with Python or Java is required."))
        self.assertEqual(self.codes("No Java required, Python is required."), {"PYTHON"})
        self.assertEqual(self.codes("Qualifications: Python is required, Java is not required."), {"PYTHON"})
        self.assertEqual(self.codes("No Python experience required; Java preferred."), {"JAVA"})

    def test_negated_use_and_vietnamese_requirement(self):
        self.assertFalse(self.codes("Responsibilities: You will not use Python."))
        self.assertFalse(self.codes("Yêu cầu: Không yêu cầu Python."))

    def test_not_only_and_no_less_than_are_not_negation(self):
        self.assertEqual(self.codes("Qualifications: Python is not only useful but important."), {"PYTHON"})
        self.assertEqual(self.codes("Qualifications: No less than five years Python experience."), {"PYTHON"})

    def test_repeated_hits_and_aliases_produce_one_job_skill(self):
        r = self.extract("Requirements: Python and Python.\nResponsibilities: Use Python.\nRequirements: NodeJS and Node.js.")
        by_code = {x["skill_code"]: x for x in r["job_skills"]}
        self.assertEqual(len(by_code), 2)
        self.assertEqual(by_code["PYTHON"]["evidence_count"], 3)
        self.assertEqual(by_code["NODEJS"]["evidence_count"], 2)
        self.assertEqual(len({e["evidence_id"] for e in r["evidence"]}), len(r["evidence"]))

    def test_html_entities_inline_tags_unicode_and_exact_mapping(self):
        raw = "<h2>Qualifications:</h2><p>😀 Cafe\u0301: Experience with <b>Python</b>, C&#43;&#43; and Node&#46;js.</p>"
        r = self.extract(raw)
        self.assertEqual({x["skill_code"] for x in r["job_skills"]}, {"PYTHON", "CPP", "NODEJS"})
        for e in r["evidence"]:
            self.assertEqual(e["excerpt"], raw[e["raw_excerpt_start"]:e["raw_excerpt_end"]])
            self.assertEqual(e["matched_text"], "".join(raw[a:b] for a, b in e["raw_match_ranges"]))
            self.assertEqual(e["source_text_sha256"], hashlib.sha256(raw.encode("utf-8")).hexdigest())
            self.assertEqual(e["mapping_status"], "MAPPED_TO_RAW")
        cpp = next(e for e in r["evidence"] if e["skill_code"] == "CPP")
        self.assertEqual(cpp["matched_text"], "C&#43;&#43;")

    def test_alias_can_cross_inline_markup_with_disjoint_ranges(self):
        raw = "<p>Requirements: Node<b>.js</b> experience.</p>"
        r = self.extract(raw)
        self.assertEqual({x["skill_code"] for x in r["job_skills"]}, {"NODEJS"})
        self.assertEqual(len(r["evidence"][0]["raw_match_ranges"]), 2)

    def test_script_and_style_content_not_matched(self):
        r = self.extract("<script>Python</script><style>Java</style><p>Requirements: SQL.</p>")
        self.assertEqual({x["skill_code"] for x in r["job_skills"]}, {"SQL"})

    def test_long_descriptions_do_not_drop_tail_skills(self):
        raw = "Qualifications: " + "detail " * 300 + "Python experience and SQL knowledge."
        r = self.extract(raw)
        self.assertEqual({x["skill_code"] for x in r["job_skills"]}, {"PYTHON", "SQL"})
        self.assertGreater(r["processing"]["long_units_retained"], 0)
        self.assertEqual(r["processing"]["dropped_oversize_units"], 0)
        self.assertEqual(r["processing"]["source_status"], "PROCESSED_WITH_MATCH")

    def test_line_endings_and_numbered_bullets(self):
        for separator in ["\n", "\r\n", "\r", "\u2028", "\u2029"]:
            with self.subTest(separator=repr(separator)):
                self.assertEqual(self.codes("Requirements:" + separator + "1. Python experience" + separator + "2. SQL knowledge"), {"PYTHON", "SQL"})

    def test_missing_failed_and_no_match_are_distinct(self):
        for raw in [None, "", " n/a ", "NULL"]:
            r = self.extract(raw)
            self.assertEqual(r["processing"]["source_status"], "SOURCE_MISSING")
            self.assertIsNone(r["processing"]["technical_skills"])
        r = self.extract(42)
        self.assertEqual(r["processing"]["source_status"], "FAILED")
        self.assertIsNone(r["processing"]["technical_skills"])
        r = self.extract("Responsibilities: Maintain equipment.")
        self.assertEqual(r["processing"]["source_status"], "PROCESSED_NO_MATCH")
        self.assertEqual(r["processing"]["technical_skills"], [])

    def test_unclosed_suppressed_html_is_partial_not_zero_hit(self):
        r = self.extract("<script>Python")
        self.assertEqual(r["processing"]["source_status"], "PARTIAL")
        self.assertIsNone(r["processing"]["technical_skills"])
        self.assertTrue(r["processing"]["review_required"])

    def test_no_identifier_or_employer_whitelist(self):
        a = self.extract("Requirements: Python experience.", "101")
        b = self.extract("Requirements: Python experience.", "202")
        self.assertEqual(a["processing"]["technical_skills"], b["processing"]["technical_skills"])
        for employer in ["Example One", "Example Two"]:
            self.assertEqual(self.codes("About us:\n" + employer + " builds Python products.\nRequirements:\nJava experience."), {"JAVA"})

    def test_invalid_dictionary_fails_closed(self):
        original = self.model.config
        for change in ["duplicate", "source", "schema"]:
            c = copy.deepcopy(original)
            if change == "duplicate":
                c["skills"][0]["aliases"].append(dict(text="java"))
            elif change == "source":
                c["source_fields"].append("postings.title")
            else:
                c["schema_version"] = 2
            with self.assertRaises(ValueError):
                TechSkillExtractor(config_bytes=json.dumps(c).encode("utf-8"))

    def test_development_outputs_preserve_grain_states_and_refuse_overwrite(self):
        from prepare_a05 import write_outputs
        inputs = {"101":dict(title="Example"),"202":dict(title="Missing description")}
        results = {"101":self.extract("Requirements: Python and Python."),
                   "202":self.extract(None,"202")}
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as folder:
            output=Path(folder)/"new-run"
            summary=write_outputs(output,self.model,inputs,results)
            self.assertEqual((summary["input_jobs"],summary["job_skill_rows"],summary["unique_job_skill_pairs"]),(2,1,1))
            with (output/"job_skill_technical.csv").open(encoding="utf-8",newline="") as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),1)
            self.assertEqual(json.loads(rows[0]["mention_types"]),["REQUIRED"])
            states=[json.loads(line) for line in (output/"skill_source_processing.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(states),2)
            self.assertIsNone(states[1]["technical_skills"])
            with self.assertRaises(FileExistsError):
                write_outputs(output,self.model,inputs,results)

    def test_raw_subset_selection_checks_full_text_and_duplicate_keys(self):
        from prepare_a05 import raw_for_jobs
        expected={"101":dict(title="Example",description="Requirements: Python.")}
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as folder:
            path=Path(folder)/"raw.csv"
            def write(rows):
                with path.open("w",encoding="utf-8",newline="") as stream:
                    writer=csv.DictWriter(stream,fieldnames=["job_id","title","description"])
                    writer.writeheader();writer.writerows(rows)
            row=dict(job_id="101",**expected["101"])
            write([row,dict(job_id="999",title="Other",description="Java")])
            found,scanned=raw_for_jobs(path,expected)
            self.assertEqual(set(found),{"101"});self.assertEqual(scanned,2)
            write([row,row])
            with self.assertRaises(ValueError):raw_for_jobs(path,expected)
            write([dict(row,description="Changed")])
            with self.assertRaises(ValueError):raw_for_jobs(path,expected)

    def test_spark_record_conversion_without_claiming_spark_execution(self):
        from a05_spark import spark_record
        result=self.extract("Requirements: Python.")
        converted=spark_record(result["job_skills"][0])
        self.assertEqual(converted["job_id"],101)
        self.assertEqual(converted["evidence_ids"],result["job_skills"][0]["evidence_ids"])
        with self.assertRaises(ValueError):spark_record(dict(job_id=None))

    def test_objective_c_with_spaces_is_not_c(self):
        self.assertEqual(self.codes("Requirements: Proficient in Objective- C, C# and Java."), {"CSHARP","JAVA"})
        self.assertEqual(self.codes("Requirements: Objective-C and Python experience."), {"PYTHON"})

    def test_company_reference_later_in_owned_task_does_not_block_skills(self):
        text="Design, develop, and maintain software applications in Java/JavaScript/SQL for the company."
        self.assertEqual(self.codes(text),{"JAVA","JAVASCRIPT","SQL"})
        self.assertTrue(all(e["mention_type"]=="TASK" for e in self.extract(text)["evidence"]))

    def test_business_requirements_are_not_candidate_requirements(self):
        text="Responsibilities: Architect and implement solutions to meet business requirements using PHP and JavaScript."
        self.assertTrue(all(e["mention_type"]=="TASK" for e in self.extract(text)["evidence"]))

    def test_preferred_suffix_does_not_propagate_across_long_content(self):
        text="Qualifications: Strong database knowledge especially SQL Server " + "detail "*40 + "other tools are a plus."
        evidence=self.extract(text)["evidence"]
        self.assertEqual(evidence[0]["mention_type"],"REQUIRED")

    def test_mixed_long_task_and_qualification_unit_requires_review(self):
        text="Responsibilities using Java " + "detail "*90 + "Minimum qualifications required Python experience."
        r=self.extract(text)
        self.assertFalse(r["job_skills"])
        self.assertTrue(all(e["mention_type"]=="AMBIGUOUS_SCOPE" for e in r["evidence"]))

    def test_explicit_what_you_need_resets_company_to_requirements(self):
        r=self.extract("Who We Are:\nOur company builds products.\nWhat You Need\nExperience in using Spark and Hadoop.\nKnowledge of Python.")
        self.assertEqual({x["skill_code"] for x in r["job_skills"]},{"SPARK","HADOOP","PYTHON"})
        self.assertTrue(all(e["section"]=="REQUIREMENTS" and e["mention_type"]=="REQUIRED" for e in r["evidence"]))

    def test_what_you_need_inside_company_sentence_is_not_a_heading(self):
        self.assertFalse(self.codes("About us: Our company knows what you need in Python products."))

    def test_other_developers_experience_does_not_turn_task_into_requirement(self):
        text="Responsibilities: Work with developers with deep experience in microservices. Utilize Python and SQL."
        r=self.extract(text)
        self.assertTrue(all(e["mention_type"]=="TASK" for e in r["evidence"]))

    def test_candidate_prefix_in_task_section_remains_requirement(self):
        r=self.extract("Responsibilities: Strong experience in Python and SQL.")
        self.assertTrue(all(e["mention_type"]=="REQUIRED" for e in r["evidence"]))


if __name__ == "__main__":
    unittest.main()
