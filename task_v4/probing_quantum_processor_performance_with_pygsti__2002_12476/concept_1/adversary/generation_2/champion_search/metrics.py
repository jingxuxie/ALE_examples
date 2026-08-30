import argparse
import hashlib
import itertools
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHAMPION = ROOT / "champions/generation_2/design.json"
TARGETS = {"triple_core_reduction": 0.50, "triple_every_family_reduction": 0.30,
           "intact_mean_ratio_limit": 1.20, "private_provisional_only": True}
USABILITY_TARGETS = {"core_inverse_inflation_minimum": 0.25, "every_family_inverse_inflation_minimum": 0.20,
                     "mean_triple_to_champion_intact_maximum": 4.0, "every_family_triple_to_champion_intact_maximum": 5.0,
                     "intact_mean_ratio_limit": 1.20, "private_provisional_only": True}


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def information_state(rows, allocation):
    information = rows.transpose(0, 2, 1) @ (rows * allocation[None, :, None]) + np.eye(14) * 1e-10
    covariance = np.linalg.inv(information)
    intact = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
    return information, covariance, intact


def loss_table(rows, allocation, order, state=None, case_set=None):
    information, covariance, intact = information_state(rows, allocation) if state is None else state
    vectors = rows * np.sqrt(np.maximum(allocation, 0))[None, :, None]
    transformed = vectors @ covariance
    leverage = transformed @ vectors.transpose(0, 2, 1)
    projected = transformed[:, :, :12]
    target = projected @ projected.transpose(0, 2, 1)
    diagonal = 1 - np.diagonal(leverage, axis1=1, axis2=2)
    target_diagonal = np.diagonal(target, axis1=1, axis2=2)
    cases = np.array(list(itertools.combinations(range(len(allocation)), order)), dtype=int) if case_set is None else np.asarray(case_set, dtype=int)
    risks = np.empty((len(rows), len(cases)))
    for start in range(0, len(cases), 128):
        selected = cases[start:start + 128]
        first, second = selected[:, 0], selected[:, 1]
        first_diag, second_diag = diagonal[:, first], diagonal[:, second]
        cross = -leverage[:, first, second]
        if order == 2:
            determinant = first_diag * second_diag - cross ** 2
            numerator = second_diag * target_diagonal[:, first] + first_diag * target_diagonal[:, second] - 2 * cross * target[:, first, second]
        elif order == 3:
            third = selected[:, 2]
            third_diag = diagonal[:, third]
            first_third = -leverage[:, first, third]
            second_third = -leverage[:, second, third]
            cofactor_first = second_diag * third_diag - second_third ** 2
            cofactor_second = first_diag * third_diag - first_third ** 2
            cofactor_third = first_diag * second_diag - cross ** 2
            cofactor_cross = first_third * second_third - cross * third_diag
            cofactor_first_third = cross * second_third - second_diag * first_third
            cofactor_second_third = cross * first_third - first_diag * second_third
            determinant = first_diag * cofactor_first + cross * cofactor_cross + first_third * cofactor_first_third
            numerator = (cofactor_first * target_diagonal[:, first] + cofactor_second * target_diagonal[:, second] +
                         cofactor_third * target_diagonal[:, third] + 2 * cofactor_cross * target[:, first, second] +
                         2 * cofactor_first_third * target[:, first, third] + 2 * cofactor_second_third * target[:, second, third])
        else:
            raise ValueError("only pairs and triples are supported")
        risks[:, start:start + len(selected)] = intact[:, None] + numerator / np.maximum(determinant, 1e-24)
        invalid = (determinant <= 0) | (numerator < -1e-12)
        if np.any(invalid):
            section = risks[:, start:start + len(selected)]
            section[invalid] = 1e30
    return risks, cases, (information, covariance, intact)


def profile(features, counts, orders=(2, 3), direct=False):
    support = np.flatnonzero(counts)
    rows = features[:, support] * 8
    allocation = counts[support]
    state = information_state(rows, allocation)
    result = dict(intact=state[2], support=support)
    for order in orders:
        risks, cases, state = loss_table(rows, allocation, order, state)
        if direct:
            for position, case in enumerate(cases):
                keep = np.ones(len(support), dtype=bool)
                keep[case] = False
                risks[:, position] = information_state(rows[:, keep], allocation[keep])[2]
        worst = np.argmax(risks, axis=1)
        result[f"loss_{order}"] = risks[np.arange(len(rows)), worst]
        result[f"worst_{order}"] = support[cases[worst]]
        if not np.all(np.isfinite(result[f"loss_{order}"])) or np.any(result[f"loss_{order}"] <= 0):
            raise ValueError("invalid loss risk")
    return result


def describe(result, families):
    report = dict(scenarios=len(families), intact_mean=float(result["intact"].mean()))
    for order in [2, 3]:
        if f"loss_{order}" not in result:
            continue
        risk = result[f"loss_{order}"]
        inflation = risk / result["intact"]
        report[f"loss_{order}"] = dict(mean=float(risk.mean()), maximum=float(risk.max()),
            quantiles={str(quantile): float(np.quantile(risk, quantile)) for quantile in [0.5, 0.9, 0.95, 0.99, 0.999]},
            mean_inflation=float(inflation.mean()), maximum_inflation=float(inflation.max()),
            ratio_of_means=float(risk.mean() / result["intact"].mean()),
            family_scores={str(family): dict(mean=float(risk[families == family].mean()),
                intact_mean=float(result["intact"][families == family].mean()),
                mean_inflation=float(inflation[families == family].mean()), maximum=float(risk[families == family].max()))
                for family in np.unique(families)})
    if "loss_3" in result and "loss_2" in result:
        report["triple_to_pair_mean_ratio"] = float(result["loss_3"].mean() / result["loss_2"].mean())
        report["triple_to_pair_family_ratios"] = {str(family): float(result["loss_3"][families == family].mean() /
                                                    result["loss_2"][families == family].mean()) for family in np.unique(families)}
    return report


def compare(candidate, reference, families):
    intact_ratio = float(candidate["intact"].mean() / reference["intact"].mean())
    family_scores = {str(family): dict(candidate_mean=float(candidate["loss_3"][families == family].mean()),
                     reference_mean=float(reference["loss_3"][families == family].mean()),
                     reduction=float(1 - candidate["loss_3"][families == family].mean() / reference["loss_3"][families == family].mean()))
                     for family in np.unique(families)}
    core = float(1 - candidate["loss_3"].mean() / reference["loss_3"].mean())
    worst = min(value["reduction"] for value in family_scores.values())
    passed = core >= 0.5 and worst >= 0.3 and intact_ratio <= 1.2
    return dict(core_score=core, worst_family_score=worst, intact_mean_ratio=intact_ratio,
                candidate_triple_mean=float(candidate["loss_3"].mean()), reference_triple_mean=float(reference["loss_3"].mean()),
                intact_mean=float(candidate["intact"].mean()), reference_intact_mean=float(reference["intact"].mean()),
                family_scores=family_scores, passed=passed, targets=TARGETS,
                reason="all provisional finite-benchmark targets met" if passed else "one or more provisional targets unmet")


def usability_compare(candidate, reference, families):
    intact_ratio = float(candidate["intact"].mean() / reference["intact"].mean())
    family_scores = {str(family): dict(candidate_loss_mean=float(candidate["loss_3"][families == family].mean()),
        champion_intact_mean=float(reference["intact"][families == family].mean()),
        inverse_inflation=float(reference["intact"][families == family].mean() / candidate["loss_3"][families == family].mean()),
        inflation=float(candidate["loss_3"][families == family].mean() / reference["intact"][families == family].mean()))
        for family in np.unique(families)}
    core = float(reference["intact"].mean() / candidate["loss_3"].mean())
    worst = min(value["inverse_inflation"] for value in family_scores.values())
    passed = core >= .25 and worst >= .20 and intact_ratio <= 1.20
    return dict(core_score=core, worst_family_score=worst, intact_mean_ratio=intact_ratio,
                mean_loss_inflation=float(1 / core), candidate_triple_mean=float(candidate["loss_3"].mean()),
                champion_intact_mean=float(reference["intact"].mean()), candidate_intact_mean=float(candidate["intact"].mean()),
                family_scores=family_scores, passed=passed, targets=USABILITY_TARGETS,
                legacy_relative_reduction_diagnostic=compare(candidate, reference, families),
                reason="all provisional 4x/5x usability caps met" if passed else "one or more provisional usability caps unmet")


class Benchmark:
    def __init__(self):
        frozen_path = HERE / "provisional_contract.json"
        self.contract = json.loads(frozen_path.read_text())["physical_contract"] if frozen_path.exists() else json.loads((ROOT / "participant/input/contract.json").read_text())
        archived = ROOT / "generations/generation_1/participant/input/candidates.json"
        self.candidates = json.loads((archived if archived.exists() else ROOT / "participant/input/candidates.json").read_text())
        self.reference_counts = np.array(json.loads(CHAMPION.read_text())["batches"])
        self.champion_hash = hashlib.sha256(CHAMPION.read_bytes()).hexdigest()
        self.training_path = HERE / "training_source.npz"
        if not self.training_path.exists():
            self.training_path = ROOT / "generations/generation_1/evaluator/hidden/benchmark.npz"
        with np.load(self.training_path, allow_pickle=False) as source:
            self.features = source["features"].copy()
            self.families = source["families"].copy()
            self.parameters = source["parameters"].copy()
            self.costs = source["costs"].copy()
        self.reference = profile(self.features, self.reference_counts, direct=True)

    def validate(self, counts):
        if counts.shape != self.costs.shape or np.any(~np.isfinite(counts)) or np.any(counts != np.floor(counts)) or np.any(counts < 0) or np.any(counts > 48):
            raise ValueError("invalid batches")
        active = int(np.count_nonzero(counts))
        cost = int(counts @ self.costs + 12000 * active)
        if not 4 <= active <= 24 or cost > 1600000:
            raise ValueError("physical support or budget constraint violated")
        return cost, active

    def evaluate(self, counts, direct=True):
        cost, active = self.validate(counts)
        candidate = profile(self.features, counts, orders=(3,), direct=direct)
        score = usability_compare(candidate, self.reference, self.families)
        score.update(valid=True, execution_ticks=cost, distinct_circuits=active, total_batches=int(counts.sum()),
                     runtime_resource_score=1 - cost / 1600000, every_triple_directly_inverted=direct,
                     reference_design_sha256=self.champion_hash)
        return score

    def freeze(self):
        frozen = dict(targets=TARGETS, physical_contract=self.contract, reference_sha256=self.champion_hash,
                      hidden_data_sha256=hashlib.sha256(self.training_path.read_bytes()).hexdigest(),
                      objective="mean of per-operating-point maximum A-risk after all batches of each selected triple are lost, without reallocation",
                      authorized_completed_solver="concept_1/attempts/v_2", active_attempts_inspected=False)
        path = HERE / "provisional_contract.json"
        if path.exists() and json.loads(path.read_text()) != frozen:
            raise ValueError("provisional private contract changed")
        if not path.exists():
            write_json(path, frozen)
            (HERE / "champion_design.json").write_bytes(CHAMPION.read_bytes())
            write_json(HERE / "hidden_champion_diagnostic.json", describe(self.reference, self.families))
        usability = dict(targets=USABILITY_TARGETS, reference_sha256=self.champion_hash,
                         authoritative_task_frozen=False, main_session_decides_final_task=True)
        usability_path = HERE / "usability_contract.json"
        if usability_path.exists() and json.loads(usability_path.read_text()) != usability:
            raise ValueError("private usability target changed")
        if not usability_path.exists():
            write_json(usability_path, usability)


def root_clusters(features, counts, result, families, parameters, union, benchmark, order):
    rows = features * 8
    information, covariance, intact = information_state(rows, counts)
    lost = result[f"worst_{order}"]
    reduced = information.copy()
    for slot in range(order):
        local = lost[:, slot]
        removed = rows[np.arange(len(rows)), local]
        reduced -= counts[local, None, None] * removed[:, :, None] * removed[:, None, :]
    after = np.linalg.inv(reduced)
    increments = np.diagonal(after[:, :12, :12] - covariance[:, :12, :12], axis1=1, axis2=2)
    dominant = np.argmax(increments, axis=1)
    global_lost = union[lost]
    histogram = Counter(tuple(int(index) for index in case) for case in global_lost)
    groups = []
    for case, frequency in histogram.most_common(12):
        mask = np.all(global_lost == np.array(case)[None], axis=1)
        mean_increment = increments[mask].mean(axis=0)
        ranked = np.argsort(mean_increment)[::-1]
        groups.append(dict(circuits=list(case), operating_points=frequency,
            definitions=[benchmark.candidates[index] for index in case], families=dict(Counter(str(value) for value in families[mask])),
            mean_loss_risk=float(result[f"loss_{order}"][mask].mean()),
            mean_contribution_to_total_increase=float((result[f"loss_{order}"][mask] - intact[mask]).sum() / len(rows)),
            variance_increments=[dict(parameter=benchmark.contract["parameter_order"][index], value=float(mean_increment[index])) for index in ranked[:4]]))
    worst = int(np.argmax(result[f"loss_{order}"]))
    return dict(groups=groups, dominant_parameter_counts=dict(Counter(benchmark.contract["parameter_order"][index] for index in dominant)),
                mean_parameter_increments={name: float(value) for name, value in zip(benchmark.contract["parameter_order"][:12], increments.mean(axis=0))},
                minimum_remaining_information_eigenvalue=float(np.linalg.eigvalsh(reduced).min()),
                worst_point=dict(family=str(families[worst]), parameters=parameters[worst].tolist(),
                                 lost_circuits=global_lost[worst].tolist(), risk=float(result[f"loss_{order}"][worst]),
                                 intact=float(intact[worst])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission")
    parser.add_argument("--output")
    args = parser.parse_args()
    benchmark = Benchmark()
    benchmark.freeze()
    score = describe(benchmark.reference, benchmark.families)
    if args.submission:
        artifact = json.loads(Path(args.submission).read_text())
        if set(artifact) != {"batches"} or any(type(value) is not int for value in artifact["batches"]):
            raise ValueError("expected integral batches only")
        score = benchmark.evaluate(np.array(artifact["batches"]))
    if args.output:
        output = Path(args.output).resolve()
        if HERE not in output.parents:
            raise ValueError("output outside private write scope")
        write_json(output, score)
    print(json.dumps(score, indent=2))


if __name__ == "__main__":
    main()
