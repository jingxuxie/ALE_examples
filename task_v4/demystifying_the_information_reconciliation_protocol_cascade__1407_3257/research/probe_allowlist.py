import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def probe():
    with tempfile.TemporaryDirectory(prefix="cascade-allowlist-") as directory:
        staging = Path(directory)
        task = staging / "participant"
        output = staging / "output"
        task.mkdir()
        output.mkdir()
        forbidden = [str(ROOT / "concept_2/evaluator/hidden/privileged_witness.json"), str(ROOT / "research/sources/paper.html"), str(ROOT.parent.parent / "token")]
        forbidden += [path.replace("/srv/home/", "/home/") for path in forbidden]
        program = "import json,pathlib,socket\n"
        program += f"forbidden={forbidden!r}\n"
        program += "reads={}\nfor path in forbidden:\n try:\n  pathlib.Path(path).read_bytes(); reads[path]=True\n except OSError:\n  reads[path]=False\n"
        program += "try:\n connection=socket.socket(); connection.settimeout(1); connection.connect(('1.1.1.1',443)); network=True\nexcept OSError:\n network=False\n"
        program += "import numpy, scipy\n"
        program += f"pathlib.Path({str(output / 'probe.json')!r}).write_text(json.dumps(dict(forbidden_reads=reads,network_connected=network,numpy=numpy.__version__,scipy=scipy.__version__,output_writable=True)))\n"
        (task / "probe.py").write_text(program)
        codex = str(Path(subprocess.check_output(["which", "codex"], text=True).strip()).resolve())
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()
        allowlist = {":minimal": "read", str(task): "read", str(output): "write", str(home / "packages"): "read", str(home / "tmp/arg0"): "read", codex: "read"}
        setting = "permissions.benchmark.filesystem={" + ",".join(json.dumps(key) + "=" + json.dumps(value) for key, value in allowlist.items()) + "}"
        command = [codex, "-c", setting, "-c", 'default_permissions="benchmark"', "sandbox", "-P", "benchmark", "-C", str(task), "--", "/usr/bin/python3", str(task / "probe.py")]
        environment = dict(os.environ)
        environment.pop("CODEX_PERMISSION_PROFILE", None)
        environment.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
        started = time.monotonic()
        try:
            completed = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=180)
            report = {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "elapsed_seconds": time.monotonic() - started, "command": command}
            if (output / "probe.json").exists():
                report["probe"] = json.loads((output / "probe.json").read_text())
                report["valid"] = not any(report["probe"]["forbidden_reads"].values()) and not report["probe"]["network_connected"] and report["probe"]["output_writable"]
            else:
                report["valid"] = False
        except subprocess.TimeoutExpired:
            report = {"valid": False, "reason": "sandbox probe timed out", "elapsed_seconds": time.monotonic() - started}
        (ROOT / "research/isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    probe()
