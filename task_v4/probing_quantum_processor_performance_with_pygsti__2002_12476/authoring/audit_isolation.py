import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    participant = (ROOT / "concept_1/participant").resolve()
    output = (ROOT / "authoring/isolation_scratch").resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path(shutil.which("apply_patch")).parent / "codex-linux-sandbox"
    profile = dict(type="managed", file_system=dict(type="restricted", entries=[
        dict(path=dict(type="special", value=dict(kind="minimal")), access="read"),
        dict(path=dict(type="path", path=str(participant)), access="read"),
        dict(path=dict(type="path", path=str(output)), access="write"),
        dict(path=dict(type="path", path=str(helper.parent)), access="read"),
        dict(path=dict(type="path", path=str(helper.resolve())), access="read"),
    ]), network="restricted")
    forbidden = [ROOT / "concept_1/evaluator/hidden/benchmark.npz", ROOT / "concept_1/evaluator/evaluate.py",
                 ROOT / "authoring/concept_selection.md", ROOT.parents[1] / "tasks",
                 Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "auth.json"]
    code = (
        "import json, pathlib, socket, numpy, scipy; "
        f"forbidden={list(map(str, forbidden))!r}; "
        "results={'private_paths_invisible':all(not pathlib.Path(path).exists() for path in forbidden)}; "
        f"results['participant_visible']=pathlib.Path({str(participant / 'TASK.md')!r}).is_file(); "
        f"pathlib.Path({str(output / 'writable.txt')!r}).write_text('ok'); "
        "results['output_writable']=True; "
        "results['numpy_available']=True; "
        "results['scipy_available']=True; "
        "\ntry:\n socket.socket(socket.AF_INET,socket.SOCK_STREAM); results['network_denied']=False\n"
        "except PermissionError:\n results['network_denied']=True\n"
        "print(json.dumps(results))"
    )
    command = [str(helper), "--sandbox-policy-cwd", str(participant), "--command-cwd", str(participant),
               "--permission-profile", json.dumps(profile), "--", "/usr/bin/python3", "-c", code]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=180,
                               env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"))
    result = dict(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr,
                  profile=profile, helper=str(helper))
    if completed.returncode == 0:
        result["checks"] = json.loads(completed.stdout.strip().splitlines()[-1])
        result["passed"] = all(result["checks"].values())
    else:
        result["passed"] = False
    (ROOT / "authoring/isolation_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
