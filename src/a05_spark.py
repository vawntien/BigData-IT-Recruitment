"""A05 PySpark adapter for TV1's validated D06 it_jobs input.

Dependencies default to Spark addPyFile. An explicit, hash-verified shared
PYTHONPATH mode supports a single-host local Spark context without file shipping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tech_skill_extractor import TechSkillExtractor
from tv2_csv import ROOT, sha256, write_json


def spark_record(record):
    """Explicit Python-string -> Spark bigint conversion; no field dropping."""
    if record["job_id"] is None:
        raise ValueError("A05 output requires a non-null job_id")
    return dict(record, job_id=int(record["job_id"]))


def output_schemas():
    from pyspark.sql.types import ArrayType, BooleanType, LongType, StringType, StructField, StructType
    string, number, boolean = StringType(), LongType(), BooleanType()
    strings = ArrayType(string, containsNull=False)
    ranges = ArrayType(ArrayType(number, containsNull=False), containsNull=False)
    common = [StructField("job_id",number,False), StructField("run_id",string,False),
              StructField("dictionary_version",string,False), StructField("dictionary_sha256",string,False),
              StructField("extractor_version",string,False), StructField("source_field",string,False)]
    def schema(fields):
        return StructType(common + [StructField(name,typ,nullable) for name,typ,nullable in fields])
    return {
        "job_skill_technical": schema([
            ("skill_code",string,False),("skill_name",string,False),("skill_group",string,False),
            ("mention_types",strings,False),("evidence_ids",strings,False),("evidence_count",number,False)]),
        "technical_skill_evidence": schema([
            ("skill_code",string,False),("skill_name",string,False),("skill_group",string,False),
            ("evidence_id",string,False),("matched_alias",string,False),("matched_text",string,True),
            ("derived_matched_text",string,False),("raw_match_ranges",ranges,True),("raw_offset_unit",string,False),
            ("excerpt",string,True),("raw_excerpt_start",number,True),("raw_excerpt_end",number,True),
            ("sentence_text",string,False),("unit_index",number,False),("section",string,False),
            ("normalized_start",number,False),("normalized_end",number,False),
            ("derived_start",number,False),("derived_end",number,False),("source_text_sha256",string,False),
            ("mapping_status",string,False),("mention_type",string,False),("accepted",boolean,False),("rule_id",string,False)]),
        "skill_source_processing": schema([
            ("source_text_sha256",string,True),("source_status",string,False),("error_code",string,True),
            ("review_required",boolean,False),("accepted_skill_count",number,False),
            ("accepted_evidence_count",number,False),("excluded_evidence_count",number,False),
            ("ambiguous_evidence_count",number,False),("technical_skills",strings,True),("parser_issues",strings,False),
            ("units",number,False),("long_units_retained",number,False),("dropped_oversize_units",number,False)])}


def prepare_dependencies(sc, mode):
    """Never silently downgrade distribution or emulate filesystem permissions."""
    modules = ["tech_skill_extractor", "description_processing", "tv2_csv", "a05_spark"]
    if mode == "add_pyfile":
        for name in modules:
            sc.addPyFile(str(ROOT / "src" / (name + ".py")))
        return dict(mode=mode)
    if mode != "shared_local_pythonpath":
        raise ValueError("Unknown A05 dependency mode")
    if sc.master != "local" and not sc.master.startswith("local["):
        raise ValueError("shared_local_pythonpath is restricted to single-host local Spark")
    expected = {name: dict(path=str((ROOT / "src" / (name + ".py")).resolve()),
                           sha256=sha256(ROOT / "src" / (name + ".py"))) for name in modules}
    def probe(rows):
        import importlib
        import os
        import sys
        import hashlib
        from pathlib import Path
        observed = {}
        for name in modules:
            path = Path(importlib.import_module(name).__file__).resolve()
            observed[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        yield dict(pid=os.getpid(), python=sys.executable, modules=observed)
    probes = sc.parallelize([0, 1], 2).mapPartitions(probe).collect()
    if len(probes) != 2 or any(p["modules"] != expected for p in probes):
        raise ValueError("Python worker dependency path/hash differs from driver source")
    return dict(mode=mode, expected=expected, workers=probes, scope="SINGLE_HOST_LOCAL_ONLY")


def extract_frames(it_jobs, config_path, run_id, *, dependency_mode=None):
    """Return (tables, cached result RDD, input count); caller unpersists RDD."""
    from pyspark import StorageLevel
    from pyspark.sql import functions as F
    from pyspark.sql.types import BooleanType, LongType, StringType
    required = {"job_id","description","it_decision","is_it","taxonomy_version","taxonomy_sha256"}
    if required - set(it_jobs.columns):
        raise ValueError("D06 input is missing membership/provenance columns")
    expected_types = {"job_id":LongType,"description":StringType,"it_decision":StringType,
                      "is_it":BooleanType,"taxonomy_version":StringType,"taxonomy_sha256":StringType}
    if any(not isinstance(it_jobs.schema[name].dataType,typ) for name,typ in expected_types.items()):
        raise ValueError("Unexpected D06 input schema")
    if it_jobs.filter(F.col("job_id").isNull()).limit(1).count() or it_jobs.groupBy("job_id").count().filter("count > 1").limit(1).count():
        raise ValueError("D06 job grain is invalid")
    bad = (F.col("it_decision").isNull() | (F.col("it_decision") != "ACCEPT") |
           F.col("is_it").isNull() | (F.col("is_it") != F.lit(True)) |
           F.col("taxonomy_version").isNull() | F.col("taxonomy_sha256").isNull())
    if it_jobs.filter(bad).limit(1).count():
        raise ValueError("Supply only validated D06 ACCEPT/true jobs with taxonomy provenance")
    model = TechSkillExtractor(config_path)
    spark = it_jobs.sparkSession
    mode = dependency_mode or spark.sparkContext.getConf().get("spark.a05.dependencyMode", "add_pyfile")
    prepare_dependencies(spark.sparkContext, mode)
    payload = spark.sparkContext.broadcast(Path(config_path).read_bytes())
    def worker(rows):
        extractor = TechSkillExtractor(config_bytes=payload.value)
        for row in rows:
            yield extractor.extract(row["description"], row["job_id"], run_id=run_id)
    results = it_jobs.select("job_id","description").rdd.mapPartitions(worker).persist(StorageLevel.MEMORY_AND_DISK)
    schemas = output_schemas()
    tables = {
        "job_skill_technical":spark.createDataFrame(results.flatMap(lambda r:[spark_record(x) for x in r["job_skills"]]),schemas["job_skill_technical"]),
        "technical_skill_evidence":spark.createDataFrame(results.flatMap(lambda r:[spark_record(x) for x in r["evidence"]]),schemas["technical_skill_evidence"]),
        "skill_source_processing":spark.createDataFrame(results.map(lambda r:spark_record(r["processing"])),schemas["skill_source_processing"])}
    if hashlib.sha256(payload.value).hexdigest() != model.sha256:
        raise ValueError("Dictionary changed while preparing Spark broadcast")
    return tables, results, it_jobs.count()


def run(args):
    output = Path(args.output).resolve()
    if not output.is_relative_to((ROOT/"data/analytics").resolve()) or output.exists():
        raise ValueError("Choose a new local output directory inside data/analytics")
    # No installation, Java changes, ETL, or automatic raw fallback here.
    from d05_utils import get_spark_session
    from pyspark.sql import functions as F
    config = Path(args.config).resolve()
    model = TechSkillExtractor(config)
    spark = get_spark_session("BigDataITRecruitment-A05",ROOT)
    results = None
    try:
        it_jobs = spark.read.parquet(str(Path(args.input).resolve()))
        tables, results, input_count = extract_frames(it_jobs,config,args.run_id,dependency_mode=args.dependency_mode)
        bridge, evidence, states = (tables[k] for k in ["job_skill_technical","technical_skill_evidence","skill_source_processing"])
        counts = {name:table.count() for name,table in tables.items()}
        if bridge.select("job_id","skill_code").distinct().count()!=counts["job_skill_technical"] or counts["skill_source_processing"]!=input_count:
            raise AssertionError("Output grain/count mismatch")
        if states.filter(F.col("source_status").isin("FAILED","PARTIAL")).limit(1).count():
            raise ValueError("Resolve failed/partial extraction before publishing official Parquet")
        if evidence.filter("accepted = true").count() != (bridge.agg(F.sum("evidence_count")).first()[0] or 0):
            raise AssertionError("Evidence count mismatch")
        output.mkdir(parents=True,exist_ok=False)
        manifest = dict(status="WRITING",run_id=args.run_id,input=str(Path(args.input).resolve()),
            input_jobs=input_count,input_taxonomies=[row.asDict() for row in it_jobs.select("taxonomy_version","taxonomy_sha256").distinct().collect()],
            dictionary_version=model.version,dictionary_sha256=model.sha256,spark_version=spark.version,
            spark_executed=True,skills_desc_enabled=False,etl_rerun=False,counts=counts,
            dependency_mode=args.dependency_mode,
            adapter_sha256=sha256(ROOT/"src/a05_spark.py"),extractor_sha256=sha256(ROOT/"src/tech_skill_extractor.py"))
        write_json(output/"run_manifest.json",manifest,exclusive=True)
        try:
            for name,table in tables.items():
                table.write.mode("errorifexists").parquet(str(output/(name+".parquet")))
                saved = spark.read.parquet(str(output/(name+".parquet")))
                if saved.count()!=counts[name] or table.exceptAll(saved.select(table.columns)).limit(1).count():
                    raise AssertionError("Parquet readback content/count mismatch")
            manifest["status"]="PARQUET_WRITTEN_PENDING_REVIEW"
            write_json(output/"run_manifest.json",manifest)
        except Exception as error:
            manifest.update(status="FAILED_PARTIAL_OUTPUT",error_type=type(error).__name__)
            write_json(output/"run_manifest.json",manifest)
            raise
        print(json.dumps(manifest,ensure_ascii=False,indent=2))
    finally:
        if results is not None:
            results.unpersist()
        spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,help="TV1 validated D06 it_jobs Parquet")
    parser.add_argument("--output",required=True)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--config",default=ROOT/"config/tech_skills.json")
    parser.add_argument("--dependency-mode",choices=["add_pyfile","shared_local_pythonpath"],default="add_pyfile")
    run(parser.parse_args())
