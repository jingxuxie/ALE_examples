import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
PREVIOUS = CONCEPT / "adversary/scaling_stress"
GENERATION = CONCEPT / "generations/generation_2"


def add(relative, contents):
    destination = ROOT / relative
    if destination.exists():
        raise RuntimeError("Refusing overwrite: " + str(destination))
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n"
    patch += "".join("+" + line + "\n" for line in contents.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)


def main():
    snapshot = {}
    for base in (CONCEPT, GENERATION):
        for directory in ("participant", "evaluator"):
            for path in (base / directory).rglob("*"):
                if path.is_file():
                    snapshot[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT / "frozen_snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    add("cases.py", (PREVIOUS / "cases.py").read_text())
    add("worker_support/local_model.py", (GENERATION / "adversary/portfolio/local_model.py").read_text())
    add("validation_model.py", (GENERATION / "adversary/validation_model.py").read_text())
    helpers = (GENERATION / "adversary/science_helpers.py").read_text().replace("from case_factory import sample", "from cases import sample")
    add("science_helpers.py", helpers)
    evaluator = (PREVIOUS / "run.py").read_text()
    start, end = evaluator.index("def check_frozen():"), evaluator.index("def stress_command(")
    evaluator = evaluator[:start] + '''def check_frozen():
    expected = json.loads((SIDE / "frozen_snapshot.json").read_text())
    for name, value in expected.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == value


''' + evaluator[end:]
    add("run.py", evaluator)
    policy = (GENERATION / "adversary/portfolio/solution.py").read_text()
    policy = policy.replace('sys.path.insert(0, str(Path(__file__).resolve().parent))', 'sys.path.insert(0, "/stress_public")')
    policy = policy.replace('        allocate(np.ones(len(used)), spec["shot_budget"])',
                           '''        remaining = spec["shot_budget"]
        for action in range(len(used)):
            count = remaining // (len(used) - action)
            while count:
                shots = min(count, spec["max_shots_per_query"])
                query(action, shots)
                count -= shots
                remaining -= shots''')
    policy = policy.replace('        for action in range(len(used)):\n            query(action, 80)',
                           '''        pilot_actions = list(range(13))
        pilot_actions += [action for action in range(13, len(used)) if (action - 13) % 4 in (1, 3)]
        for action in pilot_actions:
            query(action, 80)''')
    add("workers/reference/solution.py", policy)
    (ROOT / "runs").mkdir(exist_ok=True)
    print("Private harness prepared; no frozen files or fresh submissions changed.", flush=True)


if __name__ == "__main__":
    main()
