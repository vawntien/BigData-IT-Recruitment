"""Reproducible Pilot ZIP built from pinned git blobs, distributed by Spark broadcast.

No TV2 merge/cherry-pick. Workers receive exact bytes, not driver absolute paths.
Broadcast ZIP avoids Windows Spark addPyFile -> winutils chmod dependency.
Git integration/licensing/review for Official remains a separate group decision.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

from d06_taxonomy_adapter import CODE_HASHES, CONFIG_HASH, TV2_COMMIT
from d06_pilot_runtime import PilotIntegrityError

CONFIG_NAME = "it_taxonomy_v0.2.2.json"
CONFIG_REF = f"git:{TV2_COMMIT}:config/versions/{CONFIG_NAME}"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_config(data):
    if json.loads(data)["version"] != "0.2.2":
        raise PilotIntegrityError("Unsupported taxonomy version")
    if sha(data) != CONFIG_HASH:
        raise PilotIntegrityError("Candidate config exact-byte hash mismatch")


def build_package(root: Path, config_arg=CONFIG_REF):
    files = {}
    for name, expected in CODE_HASHES.items():
        data = subprocess.check_output(["git", "show", f"{TV2_COMMIT}:src/{name}"], cwd=root)
        if sha(data) != expected:
            raise PilotIntegrityError(f"Pinned code hash mismatch: {name}")
        files[name] = data
    pinned_config = subprocess.check_output(
        ["git", "show", f"{TV2_COMMIT}:config/versions/{CONFIG_NAME}"], cwd=root)
    data = pinned_config if config_arg == CONFIG_REF else Path(config_arg).read_bytes()
    validate_config(data)
    if data != pinned_config:
        raise PilotIntegrityError("Config differs from pinned commit")
    files[CONFIG_NAME] = data
    for name in ("d06_taxonomy_adapter.py", "d06_pilot_runtime.py"):
        files[name] = (root / "src" / name).read_bytes()
    files["parity_schema.json"] = (root / "data/audit/d06/spark_schema.json").read_bytes()
    manifest = {"tv2_commit": TV2_COMMIT, "version": "0.2.2", "config_sha256": CONFIG_HASH,
                "files": {name: sha(data) for name, data in sorted(files.items())}}
    files["runtime_manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2).encode("utf8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    content = buffer.getvalue()
    checksum = sha(content)
    target = root / "tmp/d06_pilot_packages" / f"d06_runtime_{checksum}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != content:
            raise PilotIntegrityError("Existing package modified")
    else:
        with target.open("xb") as stream:
            stream.write(content)
    return target, checksum, manifest


def verified_members(package, expected_hash):
    package = Path(package)
    if not package.is_file():
        raise PilotIntegrityError("Missing classifier package")
    content = package.read_bytes()
    if sha(content) != expected_hash:
        raise PilotIntegrityError("Package SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        manifest = json.loads(z.read("runtime_manifest.json"))
        names = set(z.namelist())
        if len(names) != len(z.namelist()) or names != set(manifest["files"]) | {"runtime_manifest.json"}:
            raise PilotIntegrityError("Package members mismatch")
        if z.testzip() is not None or any(Path(n).name != n or ":" in n or "\\" in n for n in names):
            raise PilotIntegrityError("Unsafe package path/CRC")
        files = {n: z.read(n) for n in manifest["files"]}
    for name, data in files.items():
        if sha(data) != manifest["files"][name]:
            raise PilotIntegrityError(f"Package member hash mismatch: {name}")
    for name, expected in CODE_HASHES.items():
        if name not in files or sha(files[name]) != expected:
            raise PilotIntegrityError(f"Missing/wrong TV2 dependency: {name}")
    if manifest["tv2_commit"] != TV2_COMMIT:
        raise PilotIntegrityError("Wrong TV2 commit")
    validate_config(files[CONFIG_NAME])
    return files


def worker_runner(package_broadcast, expected_hash, operation="classify"):
    """By-value closure contains only resource identity, no host source path."""
    def run(rows):
        import hashlib
        import json
        import os
        from pathlib import Path
        import sys
        import tempfile
        import zipfile
        import io
        content = package_broadcast.value
        if hashlib.sha256(content).hexdigest() != expected_hash:
            raise RuntimeError("Missing/modified broadcast classifier package")
        # The entire archive hash was checked against the driver closure before
        # importing any packaged helper. Verify/extract bytes locally per worker.
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            manifest = json.loads(z.read("runtime_manifest.json"))
            directory = Path(tempfile.gettempdir()) / f"d06_runtime_{expected_hash}_{os.getpid()}"
            directory.mkdir(exist_ok=True)
            for name, checksum in manifest["files"].items():
                if Path(name).name != name or "\\" in name or ":" in name:
                    raise RuntimeError("Unsafe runtime member")
                data = z.read(name)
                if hashlib.sha256(data).hexdigest() != checksum:
                    raise RuntimeError("Runtime member hash mismatch")
                target = directory / name
                if target.is_symlink():
                    raise RuntimeError("Unsafe worker cache")
                if target.exists():
                    if target.read_bytes() != data:
                        raise RuntimeError("Worker cache differs; no overwrite")
                else:
                    with target.open("xb") as stream:
                        stream.write(data)
        sys.path.insert(0, str(directory))
        from d06_pilot_runtime import classify_partition, verify_roundtrip_partition
        schema = json.loads((directory / "parity_schema.json").read_text(encoding="utf8"))
        if operation == "classify":
            yield from classify_partition(rows, directory, schema)
        elif operation == "verify":
            yield from verify_roundtrip_partition(rows)
        else:
            raise RuntimeError("Unsupported worker operation")
    return run
