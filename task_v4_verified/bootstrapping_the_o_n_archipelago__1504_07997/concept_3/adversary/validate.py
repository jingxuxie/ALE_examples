"""Trusted protocol regression probes, not autonomous agents."""

import json
import math
from pathlib import Path
import sys

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE / "evaluator"), str(BASE / "participant" / "input")]

from evaluate import run_case
from model import BUDGET, FAMILIES, generate
from protocol import ProtocolError, answer, hello, loads, query
from scoring import aggregate, score_case


def main():
    outcomes = {}
    invalid = {
        "nan": '{"type":"measure","t":NaN,"u":[1,0]}',
        "infinity": '{"type":"measure","t":1e309,"u":[1,0]}',
        "boolean": '{"type":"measure","t":true,"u":[1,0]}',
        "duplicate": '{"type":"measure","t":1,"t":2,"u":[1,0]}',
        "nonunit": '{"type":"measure","t":1,"u":[1,1]}',
        "out_of_range": '{"type":"measure","t":0,"u":[1,0]}',
        "extra_key": '{"type":"measure","t":1,"u":[1,0],"seed":2}',
        "malformed": 'not JSON',
        "null": 'null',
        "wrong_u": '{"type":"measure","t":1,"u":"hi"}',
    }
    for name, text in invalid.items():
        try:
            query(loads(text))
        except ProtocolError:
            outcomes[name] = True
        else:
            outcomes[name] = False
    instance = generate(312, "weak_low")
    message = {
        "type": "answer", "estimate": dict(zip(hello()["targets"], instance.target())),
        "radius90": dict(zip(hello()["targets"], [0.01, 0.1, 0.1, 0.1])),
    }
    answer(message)
    entry = json.dumps(message)
    begin = "import sys,json,time\njson.loads(sys.stdin.readline())\n"
    scripts = {
        "valid_exit": begin + f"print({entry!r},flush=True)\n",
        "malformed_subprocess": begin + "print('oops',flush=True)\n",
        "nan_subprocess": begin + f"print({invalid['nan']!r},flush=True)\n",
        "oversize_line": begin + "print('x'*20000,flush=True)\n",
        "stderr_flood": begin + "sys.stderr.write('x'*70000);sys.stderr.flush()\n",
        "timeout": begin + "time.sleep(3)\n",
        "truncated_line": begin + "print('{}',end='',flush=True)\n",
        "extra_after_answer": begin + f"print({entry!r},flush=True)\nprint('{{}}',flush=True)\n",
        "nonzero_after_answer": begin + f"print({entry!r},flush=True)\nsys.exit(3)\n",
        "hang_after_answer": begin + f"print({entry!r},flush=True)\ntime.sleep(3)\n",
        "budget": begin + (
            "for index in range(73):\n"
            " print(json.dumps({'type':'measure','t':3,'u':[1,0]}),flush=True)\n"
            " sys.stdin.readline()\n"
        ),
    }
    scratch = BASE / "adversary" / ".scratch"
    scratch.mkdir(exist_ok=True)
    details = {}
    for name, script in scripts.items():
        report = run_case(
            {"id": "test", "instance": instance, "noise_seed": 498},
            BASE / "participant" / "baseline", "policy.py", BASE / "participant",
            scratch, seconds=1.3, line_seconds=0.6,
            command_override=[sys.executable, "-u", "-c", script],
        )
        outcomes[name] = (report["status"] == "ok") == (name == "valid_exit")
        if name == "budget":
            outcomes["budget_count"] = report["calls"] == BUDGET
        details[name] = report
    for family in FAMILIES:
        sample = generate(42, family)
        for time in (0.25, 2, 6):
            outcomes[f"positive_{family}_{time}"] = bool(np.linalg.eigvalsh(sample.matrix(time)).min() > 0)
        outcomes[f"reproducible_{family}"] = bool(np.array_equal(sample.matrix(2), generate(42, family).matrix(2)))
    wrapped = instance.target().copy()
    wrapped[-1] += math.pi
    score = score_case(instance, wrapped, [0.01, 0.1, 0.1, 0.1])
    outcomes["projective_scoring"] = score["point_loss"] < 1e-12
    target = json.loads((BASE / "participant" / "input" / "target.json").read_text())
    cases = [{"family": family, "status": "ok", **score} for family in FAMILIES]
    outcomes["valid_aggregation"] = aggregate(cases, target, True)["passed"]
    cases[0]["status"] = "invalid"
    outcomes["invalid_is_fatal"] = not aggregate(cases, target, True)["passed"]
    outcomes["hello_public_only"] = not any(
        key in hello() for key in ("seed", "id", "family", "truth", "parameters", "tail")
    )
    result = {"passed": all(outcomes.values()), "checks": outcomes, "subprocess_cases": details,
              "os_sandbox_tested": False}
    (BASE / "adversary" / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks": len(outcomes)}))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
