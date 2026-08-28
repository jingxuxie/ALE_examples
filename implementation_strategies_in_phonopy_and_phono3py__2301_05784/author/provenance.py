"""Record immutable source and runtime identities without exposing them publicly."""

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


records = {"recorded_utc": datetime.now(timezone.utc).isoformat(), "repositories": {},
           "runtimes": {}, "paper_sha256": digest(ROOT / "source/paper.pdf")}
for name in ["phonopy", "phono3py", "symfc"]:
    repository = ROOT / "source" / name
    revision = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    summary = subprocess.check_output(["git", "-C", str(repository), "log", "-1", "--format=%cI %s"], text=True).strip()
    records["repositories"][name] = {"revision": revision, "summary": summary}
for runtime in ["runtime", "runtime4"]:
    distributions = {
        distribution.metadata["Name"]: distribution.version
        for distribution in importlib.metadata.distributions(path=[str(ROOT / runtime)])
    }
    environment = dict(os.environ, PYTHONPATH=str(ROOT / runtime), OPENBLAS_NUM_THREADS="1")
    modules = ["numpy", "scipy", "phonopy", "symfc", "spglib"]
    if runtime == "runtime":
        modules.append("phono3py")
    script = "import importlib,json; print(json.dumps({name:importlib.import_module(name).__version__ for name in " + repr(modules) + "}))"
    actual = json.loads(subprocess.check_output([sys.executable, "-c", script],
                                               env=environment, text=True))
    distributions.update(actual)
    records["runtimes"][runtime] = distributions
    records.setdefault("runtime_notes", {})[runtime] = "Core versions verified by import; import metadata can retain superseded dist-info after target-directory upgrades."
(ROOT / "provenance.json").write_text(json.dumps(records, indent=2) + "\n")
print(json.dumps(records, indent=2))
