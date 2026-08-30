import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from protocol import run_policy
from evaluate import sandbox_command


def main():
    model = json.loads((ROOT / "participant/input/practice_models.json").read_text())[0]
    table = np.load(ROOT / "participant/input/practice.npz")["energies"][:1]
    tests = {
        "forbidden_full_space": '{"query":[255]}',
        "budget_overrun": '{"query":[63,95,111]}',
        "duplicate_query": '{"query":[7,7]}',
        "nonfinite_estimate": '{"estimate":NaN}',
        "boolean_mask": '{"query":[true]}',
        "negative_mask": '{"query":[-1]}'
    }
    results = {}
    for name, action in tests.items():
        source = "import sys\nsys.stdin.readline()\nprint(" + repr(action) + ", flush=True)\nsys.stdin.readline()\n"
        try:
            run_policy([sys.executable, "-c", source], [model], table, wall_seconds=5)
            raise AssertionError("invalid action accepted")
        except (ValueError, RuntimeError) as error:
            results[name] = str(error)
    with tempfile.TemporaryDirectory(prefix="mbe_isolation_test_") as temporary:
        directory = Path(temporary)
        forbidden = str(ROOT / "evaluator/hidden/models.json")
        code = ("import json, pathlib, socket\n"
                f"assert not pathlib.Path({forbidden!r}).exists()\n"
                "assert not pathlib.Path('/home').exists()\n"
                "assert not pathlib.Path('/srv').exists()\n"
                "import numpy, scipy\n"
                "print(json.dumps({'private_paths_absent': True, 'numeric_runtime_works': True}))\n")
        (directory / "solution.py").write_text(code)
        check = subprocess.run(sandbox_command(directory), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
        if check.returncode:
            raise RuntimeError("isolation smoke test failed: " + check.stderr)
        results["sandbox"] = json.loads(check.stdout)
    result = {"passed": True, "tests": results}
    (ROOT / "evaluator/hidden/protocol_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
