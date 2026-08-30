import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = Path(tempfile.mkdtemp(prefix="cascade-public-smoke-"))
    task = directory / "participant"
    output = directory / "output"
    shutil.copytree(ROOT / "concept_3/participant", task, ignore=shutil.ignore_patterns("__pycache__"))
    output.mkdir()
    codex = str(Path(shutil.which("codex")).resolve())
    home = Path(os.environ["CODEX_HOME"]).resolve()
    allowlist = {":minimal": "read", str(task): "read", str(output): "write", str(home / "packages"): "read", str(home / "tmp/arg0"): "read", codex: "read"}
    setting = "permissions.benchmark.filesystem={" + ",".join(json.dumps(key) + "=" + json.dumps(value) for key, value in allowlist.items()) + "}"
    command = [codex, "-c", setting, "sandbox", "-P", "benchmark", "-C", str(task), "--", "/usr/bin/python3", "-B", "workspace/dev_evaluate.py", "--policy", "baseline/policy.py", "--limit", "1", "--output", str(output / "score.json")]
    environment = dict(os.environ)
    environment.pop("CODEX_PERMISSION_PROFILE", None)
    environment.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
    started = time.monotonic()
    process = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180, env=environment)
    score = json.loads((output / "score.json").read_text()) if (output / "score.json").exists() else None
    report = {"returncode": process.returncode, "elapsed_seconds": time.monotonic() - started, "stdout": process.stdout, "stderr": process.stderr, "score": score, "passed": process.returncode == 0 and score is not None and not score["protocol_failures"], "read_only_participant": True, "private_evaluator_mounted": False, "ordinary_subprocess_public_harness": True}
    (ROOT / "concept_3/adversary/public_allowlist_smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
