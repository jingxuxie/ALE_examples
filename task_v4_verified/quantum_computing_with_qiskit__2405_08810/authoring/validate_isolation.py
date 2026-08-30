import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from run_tournament import clean_runtime
from sandbox import sandbox_command

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = Path(tempfile.mkdtemp(prefix="isolation_", dir=ROOT / "authoring"))
    participant = base / "participant"
    output = base / "output"
    participant.mkdir()
    output.mkdir()
    (participant / "public.txt").write_text("visible")
    secret = base / "secret.txt"
    secret.write_text("generation-only sentinel")
    runtime = clean_runtime(base / "runtime")
    denied = [str(secret), str(ROOT / "concept_1" / "evaluator" / "hidden" / "cases.json"), str(runtime / "auth.json"), str(ROOT / "authoring" / "sources" / "paper.pdf")]
    program = (
        "import json,pathlib,numpy,scipy; "
        f"assert pathlib.Path({str(participant / 'public.txt')!r}).read_text()=='visible'; "
        f"assert not any(pathlib.Path(path).exists() for path in {denied!r}); "
        f"pathlib.Path({str(output / 'write_probe.txt')!r}).write_text('ok'); "
        "print(json.dumps({'allowlist_denies_hidden':True,'scientific_runtime_available':True,'output_writable':True}))"
    )
    binary = Path(shutil.which("codex")).resolve()
    profile = {":minimal": "read", str(participant): "read", str(output): "write", str(runtime / "packages"): "read", str(runtime / "tmp" / "arg0"): "read", str(binary): "read"}
    encoded = ",".join(f"{json.dumps(name)}={json.dumps(access)}" for name, access in profile.items())
    command = [str(binary), "-c", "permissions.benchmark.filesystem={" + encoded + "}", "-c", 'default_permissions="benchmark"', "-c", 'approval_policy="never"', "-c", 'web_search="disabled"', "sandbox", "-P", "benchmark", "-C", str(participant), "/usr/bin/python3", "-c", program]
    environment = dict(os.environ)
    environment["CODEX_HOME"] = str(runtime)
    environment.pop("CODEX_PERMISSION_PROFILE", None)
    environment.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
    result = subprocess.run(command, env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr)
    report = {"codex_allowlist": json.loads(result.stdout), "denied_paths": denied, "stderr": result.stderr, "profile_matches_runner": True}
    (ROOT / "authoring" / "isolation_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (runtime / "auth.json").unlink(missing_ok=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
