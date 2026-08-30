import argparse
import json
import time
from pathlib import Path

import numpy as np

from search_sign import SignObjective, proposals


class StencilObjective:
    def __init__(self, beta):
        self.beta = beta
        self.stencil = [(1.0, 0.0), (0.999, -0.001), (1.001, 0.001)]
        self.cases = [SignObjective(beta * multiplier, 4.0, 1.0 + shift, 16, 0.0) for multiplier, shift in self.stencil]

    def evaluate(self, fields, mode):
        values = []
        for case in self.cases:
            products = case.products(fields)
            fugacity = np.exp(case.beta * case.chemical)
            signs, logarithms = np.linalg.slogdet(np.eye(16) + fugacity * products)
            singular_values = np.linalg.svd(products, compute_uv=False)
            normalized = logarithms - np.log1p(fugacity * singular_values).sum(axis=-1)
            sign = signs.prod(axis=1)
            margin = np.exp(normalized.min(axis=1)) if mode == "minimum" else np.exp(normalized.sum(axis=1))
            values.append(sign * margin)
        return np.max(values, axis=0)

    def record(self, fields, mode, score, elapsed, iterations, seed):
        checks = []
        for (multiplier, shift), case in zip(self.stencil, self.cases):
            products = case.products(fields)
            signs, logarithms = np.linalg.slogdet(np.eye(16) + np.exp(case.beta * case.chemical) * products)
            half_signs = np.linalg.slogdet(np.eye(16) + products)[0]
            if signs.prod() != -1 or half_signs.prod() != 1:
                raise ValueError("Three-point or half-filling control failed")
            checks.append({"beta_multiplier": multiplier, "mu_shift": shift, "spin_signs": signs[0].tolist(), "spin_logabsdet": logarithms[0].tolist(), "half_filling_spin_signs": half_signs[0].tolist()})
        return {
            "beta": self.beta,
            "interaction": 4.0,
            "chemical": 1.0,
            "slices": 16,
            "fields": fields.tolist(),
            "objective_mode": mode,
            "objective": score,
            "stencil_checks": checks,
            "seconds": elapsed,
            "iterations": iterations,
            "seed": seed,
            "high_precision_verified": False,
            "success": True,
        }


def structured_proposals(fields, random):
    candidates = proposals(fields, random, 96)
    structured = np.repeat(fields[None], 64, axis=0)
    for index, candidate in enumerate(structured):
        time_index = int(random.integers(16))
        site = int(random.integers(16))
        length = int(random.integers(2, 9))
        interval = (time_index + np.arange(length)) % 16
        if index % 4 == 0:
            candidate[interval, site] *= -1
        elif index % 4 == 1:
            horizontal, vertical = divmod(site, 4)
            sites = [4 * ((horizontal + delta_horizontal) % 4) + ((vertical + delta_vertical) % 4) for delta_horizontal, delta_vertical in [(0, 0), (0, 1), (1, 0), (1, 1)]]
            candidate[np.ix_(interval, sites)] *= -1
        elif index % 4 == 2:
            other_time = (time_index + int(random.integers(1, 5))) % 16
            candidate[[time_index, other_time]] = candidate[[other_time, time_index]]
        else:
            candidate[:, site] = np.roll(candidate[:, site], int(random.choice([-2, -1, 1, 2])))
    return np.concatenate([candidates, structured])


def run(arguments):
    random = np.random.default_rng(arguments.seed)
    payload = json.loads(arguments.start.read_text())
    seed_fields = np.asarray(payload["fields"], dtype=np.int8)
    if seed_fields.shape != (16, 16) or not np.isin(seed_fields, [-1, 1]).all():
        raise ValueError("Expected 16x16 binary fields")
    start = time.monotonic()
    beta = arguments.beta
    iterations = 0
    archive = [seed_fields.copy()]
    best_beta = None
    while time.monotonic() - start < arguments.seconds:
        objective = StencilObjective(beta)
        workers = []
        for worker_index in range(arguments.walkers):
            fields = archive[worker_index % len(archive)].copy()
            if worker_index:
                fields.reshape(-1)[random.choice(256, size=int(random.integers(2, 15)), replace=False)] *= -1
            mode = "minimum" if worker_index % 2 == 0 else "product"
            score = float(objective.evaluate(fields, mode)[0])
            workers.append({"fields": fields, "score": score, "best_fields": fields.copy(), "best_score": score, "mode": mode, "stale": 0})
        print(json.dumps({"portfolio_beta": beta, "seconds": time.monotonic() - start}), flush=True)
        stage_success = False
        stage_iterations = 0
        successful_steps = 0
        stage_best = None
        while time.monotonic() - start < arguments.seconds:
            worker = workers[stage_iterations % len(workers)]
            candidates = structured_proposals(worker["fields"], random)
            values = objective.evaluate(candidates, worker["mode"])
            selected = int(np.argmin(values))
            candidate_score = float(values[selected])
            if candidate_score < worker["score"] or random.random() < 0.15:
                worker["fields"] = candidates[selected].copy()
                worker["score"] = candidate_score
            else:
                worker["stale"] += 1
            if worker["score"] < worker["best_score"]:
                worker["best_score"] = worker["score"]
                worker["best_fields"] = worker["fields"].copy()
                worker["stale"] = 0
            if worker["stale"] >= 5:
                base = worker["best_fields"] if random.random() < 0.5 else archive[int(random.integers(len(archive)))]
                worker["fields"] = base.copy()
                count = int(random.integers(3, 25))
                worker["fields"].reshape(-1)[random.choice(256, size=count, replace=False)] *= -1
                worker["score"] = float(objective.evaluate(worker["fields"], worker["mode"])[0])
                worker["stale"] = 0
            iterations += 1
            stage_iterations += 1
            if candidate_score < -arguments.margin:
                record = objective.record(candidates[selected], worker["mode"], candidate_score, time.monotonic() - start, iterations, arguments.seed)
                if not stage_success or worker["mode"] == "product" and candidate_score < stage_best:
                    arguments.output.write_text(json.dumps(record, indent=2) + "\n")
                    arguments.output.with_name(arguments.output.stem + "_fields.json").write_text(json.dumps({"fields": record["fields"]}) + "\n")
                    print(json.dumps({"portfolio_saved": str(arguments.output), "beta": beta, "objective": candidate_score, "mode": worker["mode"], "seconds": time.monotonic() - start}), flush=True)
                    best_beta = beta
                    stage_best = candidate_score
                archive.append(candidates[selected].copy())
                archive = archive[-16:]
                stage_success = True
            if stage_success:
                successful_steps += 1
                if successful_steps >= arguments.polish:
                    break
            if stage_iterations % 24 == 0:
                print(json.dumps({"portfolio_beta": beta, "best_scores": {mode: min(worker["best_score"] for worker in workers if worker["mode"] == mode) for mode in ["minimum", "product"]}, "iterations": iterations, "seconds": time.monotonic() - start}), flush=True)
        if not stage_success or beta <= arguments.target_beta + 1e-10:
            break
        beta = max(arguments.target_beta, round(beta - arguments.step, 8))
    print(json.dumps({"portfolio_finished": True, "best_beta": best_beta, "iterations": iterations, "seconds": time.monotonic() - start}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--beta", type=float, default=0.75)
    parser.add_argument("--target-beta", type=float, default=0.7)
    parser.add_argument("--step", type=float, default=0.005)
    parser.add_argument("--seconds", type=float, default=360)
    parser.add_argument("--walkers", type=int, default=8)
    parser.add_argument("--polish", type=int, default=16)
    parser.add_argument("--margin", type=float, default=1e-10)
    parser.add_argument("--seed", type=int, default=880712)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
