import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
PUBLIC = CONCEPT / "participant"
TEMPLATES = Path(__file__).parent / "templates"


def replace_text(path, text):
    if path.exists():
        old = path.read_text()
        patch = "*** Begin Patch\n*** Update File: " + str(path) + "\n@@\n"
        patch += "\n".join("-" + line for line in old.splitlines()) + "\n"
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "\n".join("+" + line for line in text.splitlines()) + "\n*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    audit = json.loads((CONCEPT / "adversary/generation_1/champion_audit.json").read_text())
    if "broad_private_space" not in audit or audit["broad_private_space"]["scenarios"] < 1000:
        raise ValueError("broad champion counterexample search must finish before ratcheting")
    if not (CONCEPT / "generations/generation_0/freeze_manifest.json").exists():
        raise ValueError("original generation must be archived first")
    contract = json.loads((PUBLIC / "input/contract.json").read_text())
    if contract.get("generation", 0) != 0:
        raise ValueError("this builder creates only resilience generation 1")
    contract.update(generation=1, objective="worst_two_circuit_loss_A_risk", lost_circuits=2,
                    target_core_reduction=0.50, target_worst_family_reduction=0.30,
                    intact_mean_ratio_limit=1.20, baseline="validated fresh-agent champion")
    champion_bytes = (CONCEPT / "champions/generation_1/design.json").read_bytes()
    counts = np.array(json.loads(champion_bytes)["batches"])
    spec = importlib.util.spec_from_file_location("loss_template", TEMPLATES / "loss_evaluate.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    replace_text(CONCEPT / "evaluator/evaluate.py", (TEMPLATES / "loss_evaluate.py").read_text())
    replace_text(PUBLIC / "TASK.md", (TEMPLATES / "loss_TASK.md").read_text())
    public_loss_code = "import itertools\n\nimport numpy as np\n\n\n" + inspect.getsource(checker.risk_profile)
    replace_text(PUBLIC / "workspace/resilience.py", public_loss_code)
    baseline_code = '''import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "design.json"
    Path(args.output).write_bytes(source.read_bytes())


if __name__ == "__main__":
    main()
'''
    replace_text(PUBLIC / "baseline/solve.py", baseline_code)
    check_code = '''import argparse
import json
from pathlib import Path

import numpy as np

from physics import load_assets, validate_batches
from resilience import risk_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    candidates, contract = load_assets(root)
    batches, cost = validate_batches(json.loads(Path(args.submission).read_text())["batches"], candidates, contract)
    data = np.load(root / "input/development.npz", allow_pickle=False)
    intact, loss, worst = risk_profile(data["features"], batches, contract["lost_circuits"], 64)
    families = {}
    for family in np.unique(data["families"]):
        selected = data["families"] == family
        families[str(family)] = float(1 - loss[selected].mean() / data["champion_loss_risks"][selected].mean())
    core = float(1 - loss.mean() / data["champion_loss_risks"].mean())
    ratio = float(intact.mean() / data["champion_intact_risks"].mean())
    print(json.dumps(dict(core_score=core, worst_family_score=min(families.values()), family_scores=families,
        mean_loss_risk=float(loss.mean()), mean_intact_risk=float(intact.mean()), intact_mean_ratio=ratio,
        execution_ticks=cost, passed=core >= .50 and min(families.values()) >= .30 and ratio <= 1.20), indent=2))


if __name__ == "__main__":
    main()
'''
    replace_text(PUBLIC / "workspace/check.py", check_code)
    (PUBLIC / "baseline/design.json").write_bytes(champion_bytes)
    for path in [PUBLIC / "input/contract.json", CONCEPT / "evaluator/hidden/contract.json"]:
        path.write_text(json.dumps(contract, indent=2) + "\n")
    for path in [PUBLIC / "input/development.npz", CONCEPT / "evaluator/hidden/benchmark.npz"]:
        with np.load(path, allow_pickle=False) as archive:
            data = {key: archive[key] for key in archive.files}
        intact, loss, worst = checker.risk_profile(data["features"], counts, 2, 64)
        data.update(baseline_risks=intact, champion_intact_risks=intact, champion_loss_risks=loss)
        np.savez_compressed(path, **data)
    readme = (PUBLIC / "input/README.md").read_text()
    readme = readme[:readme.index("Overall reduction is")]
    readme += '''In this generation, `champion_intact_risks` and `champion_loss_risks` are
the current baseline's intact and worst-two-circuit-loss risk vectors.
`baseline_risks` is an alias for its intact risks. All three concern development
points only. Primary reduction is 1-mean(submitted loss-risk)/mean(champion
loss-risk); the same ratio is evaluated separately in every regime. The intact
guard compares the means of intact risks. A loss removes every shot belonging to
the selected circuit, without refunding cost or allowing reallocation. The worst
lost set is chosen separately for each operating point. Fewer than two selected
circuits means all selected circuits are lost. The numerical ridge remains 1e-10.

All six regimes have equal weight. Hidden operating points follow the disclosed
sampler, with no new noise mechanism or circuit family. `workspace/resilience.py`
implements the public development objective.
'''
    replace_text(PUBLIC / "input/README.md", readme)
    results = CONCEPT / "adversary/generation_1"
    for label, artifact in [("baseline", PUBLIC / "baseline/design.json"),
                            ("initial_private_candidate", results / "proof_design_initial.json")]:
        subprocess.run([sys.executable, str(CONCEPT / "evaluator/evaluate.py"), "--submission", str(artifact),
                        "--output", str(results / (label + "_score.json"))], check=True, stdout=subprocess.PIPE)
    status = dict(concept="resilient_characterization_allocation", verification_mode="A_BASELINE_IMPROVEMENT",
                  status="built", generation=1, ratchet_generations=1, solvability="unknown",
                  targets=dict(overall_loss_risk_reduction=.50, every_regime_reduction=.30, intact_ratio_max=1.20),
                  previous_fresh_attempt="v_1", previous_fresh_status="solved",
                  champion="champions/generation_1/design.json", counterexample_search="adversary/generation_1/champion_audit.json")
    (CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    (CONCEPT / "freeze_manifest.json").unlink()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
