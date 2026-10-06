from pathlib import Path

from pyspark.sql import SparkSession


def main():
    # Xác định thư mục gốc của project
    project_root = Path(__file__).resolve().parent.parent

    postings_path = project_root / "data" / "raw" / "postings.csv"

    print("=" * 60)
    print("BIG DATA - SPARK SMOKE TEST")
    print("=" * 60)

    print(f"Project root : {project_root}")
    print(f"Input file   : {postings_path}")
    print(f"File exists  : {postings_path.exists()}")

    if not postings_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {postings_path}"
        )

    spark = (
        SparkSession.builder
        .appName("BigDataITRecruitment-SmokeTest")
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    print(f"Spark version: {spark.version}")

    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .option("multiLine", "true")
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .csv(str(postings_path))
    )

    print("\nSchema:")
    df.printSchema()

    print("\nNumber of columns:", len(df.columns))
    print("Columns:")
    print(df.columns)

    print("\nFirst 5 rows:")
    df.select(
        "job_id",
        "company_name",
        "title",
        "location",
        "formatted_experience_level",
        "remote_allowed"
    ).show(5, truncate=False)

    print("\nCounting rows...")
    row_count = df.count()

    print(f"Total rows: {row_count}")

    print("\nSmoke test completed successfully.")

    spark.stop()


if __name__ == "__main__":
    main()