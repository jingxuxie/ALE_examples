import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np

from build_resilience_generation import replace_text


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
PUBLIC = CONCEPT / "participant"
EVIDENCE = CONCEPT / "adversary/generation_2"


def main():
    decision = json.loads((EVIDENCE / "decision.json").read_text())
    assert decision["build_next_generation"] and decision["broad_failure_verified"]
    assert decision["core_target"] == .25 and decision["worst_family_target"] == .20
    assert (CONCEPT / "generations/generation_1/freeze_manifest.json").exists()
    contract = json.loads((PUBLIC / "input/contract.json").read_text())
    assert contract["generation"] == 1
    contract.pop("target_core_reduction")
    contract.pop("target_worst_family_reduction")
    contract.update(generation=2, objective="usable_worst_three_circuit_loss_A_risk", lost_circuits=3,
                    target_core_score=.25, target_worst_family_score=.20, intact_mean_ratio_limit=1.20,
                    hidden_operating_points=600, hidden_points_per_regime=100,
                    score_definition="champion intact mean A-risk divided by submitted worst-three-loss mean A-risk")
    evaluator_path = CONCEPT / "evaluator/evaluate.py"
    code = evaluator_path.read_text()
    code = code.replace('float(1 - loss[mask].mean() / data["champion_loss_risks"][mask].mean())',
                        'float(data["champion_intact_risks"][mask].mean() / loss[mask].mean())')
    code = code.replace('core_score=float(1 - loss.mean() / data["champion_loss_risks"].mean()),',
                        'core_score=float(data["champion_intact_risks"].mean() / loss.mean()),\n'
                        '                      loss_risk_reduction=float(1 - loss.mean() / data["champion_loss_risks"].mean()),\n'
                        '                      loss_to_champion_intact_ratio=float(loss.mean() / data["champion_intact_risks"].mean()),')
    code = code.replace('target_core_reduction', 'target_core_score').replace('target_worst_family_reduction', 'target_worst_family_score')
    code = code.replace('insufficient overall loss-risk reduction', 'overall fourfold loss-risk budget exceeded')
    code = code.replace('insufficient worst-regime loss-risk reduction', 'a regime exceeds its fivefold loss-risk budget')
    replace_text(evaluator_path, code)
    specification = importlib.util.spec_from_file_location("usable_evaluator", evaluator_path)
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    champion = (CONCEPT / "champions/generation_2/design.json").read_text()
    replace_text(PUBLIC / "baseline/design.json", champion)
    batches = np.array(json.loads(champion)["batches"])
    for path in (PUBLIC / "input/contract.json", CONCEPT / "evaluator/hidden/contract.json"):
        replace_text(path, json.dumps(contract, indent=2) + "\n")
    shutil.copy2(EVIDENCE / "candidate_benchmark.npz", CONCEPT / "evaluator/hidden/benchmark.npz")
    development_path = PUBLIC / "input/development.npz"
    with np.load(development_path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    intact, loss, _ = evaluator.risk_profile(data["features"], batches, 3, 64)
    data.update(baseline_risks=intact, champion_intact_risks=intact, champion_loss_risks=loss)
    np.savez_compressed(development_path, **data)
    check_path = PUBLIC / "workspace/check.py"
    check_code = check_path.read_text()
    check_code = check_code.replace('float(1 - loss[selected].mean() / data["champion_loss_risks"][selected].mean())',
                                    'float(data["champion_intact_risks"][selected].mean() / loss[selected].mean())')
    check_code = check_code.replace('float(1 - loss.mean() / data["champion_loss_risks"].mean())',
                                    'float(data["champion_intact_risks"].mean() / loss.mean())')
    check_code = check_code.replace('core >= .50 and min(families.values()) >= .30',
                                    'core >= contract["target_core_score"] and min(families.values()) >= contract["target_worst_family_score"]')
    replace_text(check_path, check_code)
    task = '''# Keep characterization usable after circuit-record loss

Design a resource-constrained characterization campaign for a quantum processor whose operating point is uncertain. The campaign must retain useful local information when any three complete circuit records are lost, without sacrificing normal-operation efficiency.

Provided assets are a physical simulator and operating-point sampler, 840 candidate experiments, a public development ensemble, and the previous-generation champion as a runnable baseline. The physical model includes coherent gate errors, decoherence, and nuisance readout parameters. The supplied champion is not a passing solution for this generation.

Submit one static `design.json` containing exactly `{"batches": [...]}`: one integer allocation per candidate, in input order. The interface and scoring definitions are in `input/README.md` and `input/contract.json`. Run `python baseline/solve.py --output PATH` to emit the baseline and `python workspace/check.py PATH` to evaluate development performance. Submitted code is never executed.

The mean worst-three-loss A-risk must be at most **four times** the champion's intact mean A-risk, and at most **five times** its intact mean within every operating regime. Your intact mean A-risk must remain within **1.20 times** the champion's. Scores are inverse risk-inflation ratios; larger is better. Hidden evaluation uses 600 operating points from the disclosed sampler, equally divided among six regimes.

Resource limits: one hour of solving time, no network, 1,600,000 execution ticks, at most 24 distinct circuits, at most 48 batches per circuit, and 64 shots per batch. No adaptive reallocation or cost refund follows a loss. These are local Fisher-information objectives, not a finite-shot estimation guarantee. No report is required.
'''
    replace_text(PUBLIC / "TASK.md", task)
    readme = (PUBLIC / "input/README.md").read_text()
    readme = readme[:readme.index("In this generation,")]
    readme += '''In this generation, `champion_intact_risks` and `champion_loss_risks` are
the current baseline's intact and worst-three-circuit-loss risk vectors.
`baseline_risks` aliases its intact risks. These arrays contain development
points only. A loss removes every shot belonging to a selected circuit, without
refunding cost or allowing reallocation. The worst lost set is chosen separately
for each operating point. If fewer than three circuits are selected, all are lost.

`core_score` = mean(champion intact risk) / mean(submitted worst-three-loss risk).
The same ratio is calculated separately in each regime; `worst_family_score` is
the minimum of those six ratios. Passing requires core >=0.25 and every regime
>=0.20. The intact guard is mean(submitted intact risk) / mean(champion intact
risk) <=1.20. Thus the primary objective is a fourfold overall and fivefold
per-regime variance-risk budget, not merely a percentage improvement over a
possibly singular lost-record baseline. Larger primary and family scores are
better. Evaluation additionally reports ordinary loss-risk reduction, execution
cost, intact risk ratio, and the worst lost sets. No numerical comparison slack
is added to the stated thresholds.

All six regimes have equal weight. The 600 hidden operating points use the
disclosed sampler, with no new noise mechanism or circuit family.
`workspace/resilience.py` implements exhaustive loss-risk evaluation.
'''
    replace_text(PUBLIC / "input/README.md", readme)
    status = dict(concept="usable_resilient_characterization_allocation", verification_mode="A_BASELINE_IMPROVEMENT",
                  status="built", generation=2, ratchet_generations=2, solvability="unknown",
                  targets=dict(core_score=.25, worst_family_score=.20, intact_mean_ratio_max=1.20),
                  previous_fresh_attempt="v_2", previous_fresh_status="solved",
                  champion="champions/generation_2/design.json",
                  counterexample_search="adversary/generation_2/decision.json")
    replace_text(CONCEPT / "status.json", json.dumps(status, indent=2) + "\n")
    (CONCEPT / "freeze_manifest.json").unlink()
    result = evaluator.evaluate(PUBLIC / "baseline/design.json")
    assert result["valid"] and not result["passed"]
    (EVIDENCE / "baseline_score.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("core_score", "worst_family_score", "intact_mean_ratio", "passed")}, indent=2))


if __name__ == "__main__":
    main()
