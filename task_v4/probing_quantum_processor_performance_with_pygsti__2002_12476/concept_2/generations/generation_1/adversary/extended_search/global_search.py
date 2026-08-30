import json
import os
import time

import numpy as np

import portfolio as search


def main():
    started = time.monotonic()
    deadline = started + 300
    try:
        cores = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {cores[-min(5, len(cores))]})
    except (AttributeError, OSError):
        pass
    counts = {"probability_batch_calls": 0, "circuit_scenario_evaluations": 0, "independent_evaluator_calls": 0,
              "completed_parameter_searches": 0, "global_processor_proposals": 0}
    original = search.SCREEN.probabilities

    def counted(parameters, encoded):
        counts["probability_batch_calls"] += 1
        counts["circuit_scenario_evaluations"] += len(encoded)
        return original(parameters, encoded)

    search.SCREEN.probabilities = counted
    generator = np.random.default_rng(324412)
    seed = json.loads((search.OUTPUT / "reorder_best_witness.json").read_text())
    best_witness = seed
    best = search.EVALUATOR.score_witness(seed)
    counts["independent_evaluator_calls"] += 1
    calibration = search.SCREEN.encode(sum(search.SCREEN.FAMILIES.values(), []))
    proposals = []
    for index in range(64):
        if time.monotonic() > started + 100:
            break
        parameters = np.asarray(seed["gate_parameters"]).copy()
        parameters[:, 0] += generator.normal(0, .15 + .5 * (index % 3), 3)
        if index % 4 == 3:
            parameters[:, 0] = generator.uniform(-np.pi, np.pi, 3)
        parameters[:, 0] = (parameters[:, 0] + np.pi) % (2 * np.pi) - np.pi
        parameters[:, 1:] += generator.normal(0, .004, (3, 4))
        parameters[:, 1:] *= 1.4
        for iteration in range(3):
            results = search.SEARCH.data(parameters, calibration)
            factor = 1.
            for residual, leakage in results:
                factor = min(factor, np.sqrt(.0047 / max(abs(residual))))
                offset = 0
                for family in search.SCREEN.FAMILIES.values():
                    rms = np.sqrt(np.mean(residual[offset:offset + len(family)] ** 2))
                    factor = min(factor, np.sqrt(.00185 / max(rms, 1e-30)))
                    offset += len(family)
            parameters[:, 1:] *= factor
        word = search.SEARCH.circuit_search(parameters, seed["circuit"], generator, rounds=70, population=512)
        witness = {"version": 1, "gate_parameters": parameters.tolist(), "circuit": word}
        result = search.SCREEN.measure(witness)
        counts["global_processor_proposals"] += 1
        score = result["worst_family_score"] - 5 * max(-search.margins(result)["final_leakage_margin"], 0)
        proposals.append({"score": score, "witness": witness})
    proposals.sort(key=lambda proposal: proposal["score"], reverse=True)
    search.save("global_proposals.json", proposals)
    history = []
    try:
        for index, proposal in enumerate(proposals[:7]):
            witness = proposal["witness"]
            candidate, measured, success, evaluations = search.optimize_parameters(witness["gate_parameters"], witness["circuit"], 1, deadline)
            counts["completed_parameter_searches"] += 1
            witness = {"version": 1, "gate_parameters": candidate.reshape(3, 5).tolist(), "circuit": witness["circuit"]}
            result = search.EVALUATOR.score_witness(witness)
            counts["independent_evaluator_calls"] += 1
            record = {"index": index, "optimizer_function_evaluations": evaluations, "solver_success": success,
                      "core_score": result["core_score"], "worst_family_score": result["worst_family_score"],
                      "passed": result["passed"], "margins": search.margins(result), "seconds": time.monotonic() - started}
            history.append(record)
            search.save("global_history.json", history)
            print(json.dumps(record), flush=True)
            if search.feasible(result) and result["worst_family_score"] > best["worst_family_score"]:
                best = result
                best_witness = witness
            if result["passed"]:
                break
    except TimeoutError:
        pass
    search.save("global_best_witness.json", best_witness)
    search.save("global_best_evaluation.json", best)
    search.save("global_summary.json", {"runtime_seconds": time.monotonic() - started, "counts": counts,
                                         "core_score": best["core_score"], "worst_family_score": best["worst_family_score"],
                                         "passed": best["passed"], "margins": search.margins(best)})


if __name__ == "__main__":
    main()
