import json
import os
import shutil
import sys
from pathlib import Path


def main():
    solver = Path(os.environ["BENCHMARK_SOLVER"]).resolve()
    participant = Path(os.environ["BENCHMARK_PARTICIPANT"]).resolve()
    helper_name = os.environ.get("BENCHMARK_SANDBOX") or shutil.which("codex-linux-sandbox")
    if not helper_name:
        raise RuntimeError("Set BENCHMARK_SANDBOX to the installed codex-linux-sandbox helper")
    helper = Path(helper_name).absolute()
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    entries = [{"path":{"type":"special","value":{"kind":"minimal"}},"access":"read"}]
    for path, access in [(participant,"read"), (solver.parent,"write"),
                         (codex_home/"packages","read"), (helper.parent,"read"),
                         (helper.resolve(),"read")]:
        entries.append({"path":{"type":"path","path":str(path)},"access":access})
    for flag in ["--input", "--output"]:
        if flag in sys.argv:
            argument_path = Path(sys.argv[sys.argv.index(flag)+1]).resolve()
            path = argument_path if flag == "--input" and argument_path.is_dir() else argument_path.parent
            entries.append({"path":{"type":"path","path":str(path)},"access":"write"})
    profile = {"type":"managed", "file_system":{"type":"restricted", "entries":entries}, "network":"restricted"}
    environment = dict(os.environ)
    for name in ["CODEX_PERMISSION_PROFILE", "CODEX_SANDBOX_NETWORK_DISABLED"]:
        environment.pop(name, None)
    command = [str(helper), "--sandbox-policy-cwd", str(participant),
               "--permission-profile", json.dumps(profile), "--", sys.executable,
               str(solver), *sys.argv[1:]]
    os.chdir(solver.parent)
    os.execve(str(helper), command, environment)


if __name__ == "__main__":
    main()
