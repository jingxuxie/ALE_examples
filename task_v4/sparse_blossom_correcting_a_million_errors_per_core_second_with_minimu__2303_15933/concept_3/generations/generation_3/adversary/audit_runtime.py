import sys

sys.dont_write_bytecode = True

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import run_episode, worker_command


def main():
    episode = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"][0]
    submission = ROOT / "adversary/runtime_audit/submission"
    base = ["/usr/bin/python3", "/submission/solution.py"]
    burn = run_episode(episode, submission, base + ["--burn", "2"])
    assert burn["valid"] and 1.95 < burn["cpu_seconds"] < 3.0, burn
    enforced = run_episode(episode, submission, base + ["--burn", "2"], cpu_limit=1)
    assert not enforced["valid"] and 0.8 < enforced["cpu_seconds"] < 1.5, enforced
    memory = run_episode(episode, submission, base + ["--memory"])
    assert memory["valid"], memory
    for parent in (ROOT / "attempts", ROOT / "adversary"):
        try:
            worker_command(parent, base)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsafe parent mount accepted")
    leaf = ROOT / "attempts/audit_leaf"
    leaf.mkdir(exist_ok=True)
    command = worker_command(leaf, base)
    assert str(leaf) in command and str(ROOT / "attempts") not in command
    output = {"passed": True, "two_second_process_cpu": burn, "one_second_limit_enforced": enforced,
              "memory_and_isolation": memory, "attempt_leaf_accepted_parent_rejected": True,
              "qualification": "Infrastructure audit only, not accuracy qualification."}
    (ROOT / "adversary/validation/runtime_audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output), flush=True)


if __name__ == "__main__":
    main()
