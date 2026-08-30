import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
sys.path.insert(0, str(ROOT / "evaluator"))
from model import Model, walsh
from hidden.simulator import independent_pmf, sample_events


def design_bound(fisher, allocations, families):
    information = np.einsum("a,akl->kl", allocations, fisher)
    values = np.linalg.eigvalsh(information)
    covariance = np.linalg.inv(information)
    diagonal = np.maximum(np.diag(covariance), 0.0)
    family_rmse = {family: float(np.sqrt(np.mean(diagonal[np.array(families) == family])))
                   for family in set(families)}
    return {"rank": int(np.linalg.matrix_rank(information)), "min_eigenvalue": float(values[0]),
            "condition_number": float(values[-1] / values[0]), "local_log_crb_family": family_rmse}


def main():
    started = time.process_time()
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    results = []
    rng = np.random.default_rng(98151)
    for episode in episodes:
        spec = episode["spec"]
        rates = np.array(episode["rates"])
        model = Model(spec)
        probability, jacobian = model.distribution(np.log(rates), gradient=True)
        channel_count = len(rates)
        action_count = len(spec["actions"])
        assert np.allclose(probability.sum(axis=1), 1.0, atol=1e-12)
        assert np.allclose(jacobian.sum(axis=2), 0.0, atol=1e-12)
        independent = np.stack([independent_pmf(spec, rates, action) for action in range(action_count)])
        pmf_error = float(np.max(np.abs(probability - independent)))
        assert pmf_error < 2e-12
        direction = rng.normal(size=channel_count)
        epsilon = 1e-5
        finite_difference = (model.distribution(np.log(rates) + epsilon * direction)
                             - model.distribution(np.log(rates) - epsilon * direction)) / (2.0 * epsilon)
        gradient_error = float(np.max(np.abs(finite_difference - np.einsum("aks,k->as", jacobian, direction))))
        assert gradient_error < 1e-8
        matrix = jacobian.transpose(0, 2, 1).reshape(-1, channel_count)
        full_rank = int(np.linalg.matrix_rank(matrix, tol=1e-9))
        reference_rank = int(np.linalg.matrix_rank(jacobian[0], tol=1e-9))
        assert full_rank == channel_count
        assert reference_rank < channel_count
        fisher = model.fisher(np.log(rates))
        uniform = np.full(action_count, spec["shot_budget"] / action_count)
        selective = uniform * 0.25
        selective[11] += spec["shot_budget"] * 0.75
        oracle = np.full(action_count, 100.0)
        families = [channel["family"] for channel in spec["channels"]]
        weights = np.array([1.0 / families.count(family) for family in families])
        for allocation in range(int((spec["shot_budget"] - oracle.sum()) // 100)):
            information = np.einsum("a,akl->kl", oracle, fisher)
            risks = np.einsum("akk,k->a", np.linalg.inv(information[None] + 100.0 * fisher), weights)
            oracle[np.argmin(risks)] += 100
        sampler_z = 0.0
        if episode["id"].endswith("_0"):
            for action in (0, 3, 10, 11):
                shots = 150000
                counts = sample_events(spec, rates, action, shots, rng)
                moment = walsh(counts / shots)
                expected_moment = walsh(probability[action])
                deviation = np.sqrt(np.maximum(1.0 - expected_moment**2, 1e-14) / shots)
                sampler_z = max(sampler_z, float(np.max(np.abs(moment[1:] - expected_moment[1:]) / deviation[1:])))
                independent_counts = rng.multinomial(shots, independent[action])
                independent_moment = walsh(independent_counts / shots)
                assert np.max(np.abs(independent_moment[1:] - expected_moment[1:]) / deviation[1:]) < 7.0
            assert sampler_z < 7.0
        results.append({"id": episode["id"], "channels": channel_count, "full_jacobian_rank": full_rank,
                        "reference_jacobian_rank": reference_rank, "pmf_max_error": pmf_error,
                        "gradient_max_error": gradient_error, "sampler_max_z": sampler_z,
                        "uniform_40000": design_bound(fisher, uniform, families),
                        "action11_heavy_40000": design_bound(fisher, selective, families),
                        "true_rate_design_diagnostic_only": design_bound(fisher, oracle, families)})
        print(episode["id"], full_rank, reference_rank, flush=True)
    output = {"passed": True, "cpu_seconds": time.process_time() - started, "episodes": results,
              "warning": "Local true-rate Fisher bounds and oracle allocations are information diagnostics, NOT latent-blind passing evidence."}
    (ROOT / "adversary/science_report.json").write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
