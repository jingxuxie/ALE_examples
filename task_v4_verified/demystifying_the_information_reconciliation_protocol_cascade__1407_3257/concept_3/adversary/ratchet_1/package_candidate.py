"""Build a generation-two candidate without touching the live task."""

import hashlib
import json
from pathlib import Path

from public_development import PUBLIC_ROOT_SEED, generate
from ratchet import ARCHIVE, HERE, TASK, asset, encoded


def main():
    profile = HERE / "profiles/moderate480"
    candidate = HERE / "candidate"
    contract = json.loads((profile / "participant/input/contract.json").read_text())
    assert contract["contamination_denominators"] == [8, 6, 4]
    assert contract["parity_queries"] == 480 and contract["frames"] == 160
    for relative in ("participant/input/contract.json", "participant/input/simulator.py", "evaluator/evaluate.py", "evaluator/hidden/manifest.json"):
        asset(candidate / relative, (profile / relative).read_text())
    for relative in ("participant/baseline/policy.py", "participant/workspace/README.md", "participant/workspace/dev_evaluate.py"):
        asset(candidate / relative, (ARCHIVE / relative).read_text())
    interface = (ARCHIVE / "participant/workspace/INTERFACE.md").read_text()
    interface = interface.replace("probability 0, 1/32, or 1/16", "probability 1/8, 1/6, or 1/4")
    asset(candidate / "participant/workspace/INTERFACE.md", interface)
    task_text = (ARCHIVE / "participant/TASK.md").read_text()
    task_text += "\nGeneration two changes only the background-contamination operating regime:\nits hidden probability is one of **1/8, 1/6, or 1/4**, fixed for an episode.\nThese are synthetic experimental conditions, not measured QKD noise rates.\nAll frame, parity, mask, runtime and fixed accuracy targets remain unchanged.\nThe 36 public development cases are independently generated and labeled;\nnone is a hidden evaluation case. Solvability at this target is not certified.\n"
    asset(candidate / "participant/TASK.md", task_text)
    public_cases = generate(contract)
    asset(candidate / "participant/input/dev_cases.json", encoded(public_cases))
    asset(candidate / "participant/workspace/generate_dev_cases.py", (HERE / "public_development.py").read_text())
    test_source = (TASK / "evaluator/tests/test_contract.py").read_text()
    test_source = test_source.replace('Device("RS", 32,', 'Device("RS", CONTRACT["contamination_denominators"][0],')
    test_source = test_source.replace('Device("RR", 0,', 'Device("RR", CONTRACT["contamination_denominators"][0],')
    test_source = test_source.replace('"contamination_denominator": 0, "seed": 123', '"contamination_denominator": CONTRACT["contamination_denominators"][0], "seed": 123')
    asset(candidate / "evaluator/tests/test_contract.py", test_source)
    for name in ("isolation_probe.py", "oversized_policy.py", "idle_policy.py"):
        asset(candidate / "adversary" / name, (TASK / "adversary" / name).read_text())
    public_seeds = {case["seed"] for case in public_cases}
    private_seeds = set()
    for path in (HERE / "reports").glob("*/private_cases.json"):
        private_seeds.update(case["seed"] for case in json.loads(path.read_text()))
    assert not public_seeds & private_seeds
    frozen_files = sorted(path for path in candidate.rglob("*") if path.is_file() and path.name != "frozen.json")
    frozen = {"frozen_at_utc": "2026-08-28", "target_frozen_before_fresh": True, "sha256": {str(path.relative_to(candidate)): hashlib.sha256(path.read_bytes()).hexdigest() for path in frozen_files}}
    asset(candidate / "evaluator/frozen.json", encoded(frozen))
    asset(HERE / "public_development_generation.json", encoded({"root_seed": PUBLIC_ROOT_SEED, "episodes_per_cell": 4, "episodes": 36, "seed_recipe": "int.from_bytes(sha256(f'{public_root_seed}:{family}:{denominator}:{replicate}'.encode()).digest(), 'big')", "ordering": "replicate, family, denominator", "private_seed_overlap": 0, "private_seeds_checked": len(private_seeds), "during_private_sweeps": "Only the unchanged generation-one public dev_cases.json was mounted; new public cases are separate release assets.", "release_command_from_candidate_participant": "python3 -B workspace/generate_dev_cases.py --contract input/contract.json --output input/dev_cases.json --episodes-per-cell 4"}))
    print("Candidate assets prepared; no live files changed.")


if __name__ == "__main__":
    main()
