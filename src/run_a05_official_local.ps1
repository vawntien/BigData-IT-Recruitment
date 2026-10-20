param(
    [Parameter(Mandatory=$true)][string]$Receipt,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [Parameter(Mandatory=$true)][string]$RunId,
    [Parameter(Mandatory=$true)][string]$LogPath
)
# Same single-host environment as verified run02; no system setting changes.
$ErrorActionPreference = 'Stop'
if ((Test-Path -LiteralPath $OutputDirectory) -or (Test-Path -LiteralPath $LogPath)) { throw 'Choose new output/log paths' }
$jdkPath = (Resolve-Path 'tmp/tv2_d05_receipt_457f90ae/runtime/jdk-21.0.12.1+1').Path
$env:JAVA_HOME = $jdkPath
$env:PATH = "$jdkPath/bin;$env:PATH"
$env:PYSPARK_PYTHON = (Resolve-Path '.venv/Scripts/python.exe').Path
$env:PYSPARK_DRIVER_PYTHON = $env:PYSPARK_PYTHON
$env:PYTHONPATH = (Resolve-Path 'src').Path
$env:SPARK_LOCAL_IP = '127.0.0.1'
$env:PYSPARK_SUBMIT_ARGS = '--driver-memory 3g --conf spark.default.parallelism=2 --conf spark.sql.shuffle.partitions=2 --conf spark.python.worker.faulthandler.enabled=true --conf spark.ui.enabled=false pyspark-shell'
$ErrorActionPreference = 'Continue'
& $env:PYSPARK_PYTHON src/run_a05_official.py --receipt $Receipt --output $OutputDirectory --run-id $RunId --dependency-mode shared_local_pythonpath *> $LogPath
exit $LASTEXITCODE
