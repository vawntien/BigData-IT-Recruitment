"""Validate an explicitly approved D06 receipt; never execute classification/ETL."""
import argparse
import json
from pathlib import Path
from d06_handoff_validation import receipt_errors,verify_artifacts,validate_frames
from tv2_csv import ROOT,sha256


def main(receipt_path,output):
    out=Path(output).resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must stay inside repository')
    out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    result=dict(status='BLOCKED_DEPENDENCY',receipt_sha256=sha256(Path(receipt_path)),
                missing=receipt_errors(receipt),taxonomy_executed=False,a05_executed=False,parquet_written=False)
    spark=None
    try:
        if result['missing']:return 2
        verify_artifacts(receipt)
        from d05_utils import get_spark_session
        spark=get_spark_session('TV2-D06-RECEIVING-VALIDATION',ROOT)
        d=spark.read.parquet(receipt['it_jobs'])
        canonical=spark.read.parquet(receipt['canonical_jobs'])
        view=validate_frames(d,canonical,receipt)
        result.update(status='PASS_RECEIVING_CHECKS',input_jobs=view.count(),schema=view.schema.jsonValue(),
                      a05_description_column=receipt['a05_description_column'],job_functions_contract=receipt['job_functions_contract'])
        return 0
    except Exception as error:
        result.update(status='FAILED_RECEIVING_CHECKS',error=repr(error));raise
    finally:
        if spark:spark.stop()
        (out/'receiving_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();raise SystemExit(main(a.receipt,a.output))
