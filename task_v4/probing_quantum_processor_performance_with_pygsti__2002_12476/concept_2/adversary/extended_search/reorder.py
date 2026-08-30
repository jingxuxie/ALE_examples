import json
import os
import time

import numpy as np

import portfolio as search


def explore(parameters, word, generator, deadline, population=1536, rounds=320):
    encoded = generator.integers(0, 3, size=(population, 64))
    seed = search.SCREEN.encode([word])[0]
    encoded[:population // 2] = seed
    best_word = word
    best_score = -np.inf
    for generation in range(rounds):
        if time.monotonic() > deadline:
            raise TimeoutError("bounded reorder search")
        results = search.SEARCH.data(parameters, encoded)
        gaps = np.min([abs(residual) for residual, leakage in results], axis=0)
        excess = np.maximum(np.max([leakage for residual, leakage in results], axis=0) - .0099, 0)
        scores = gaps - 5 * excess
        for gate in range(3):
            scores -= np.maximum(4 - np.sum(encoded == gate, axis=1), 0)
        winner = int(np.argmax(scores))
        if scores[winner] > best_score:
            best_score = float(scores[winner])
            best_word = "".join("IXY"[index] for index in encoded[winner])
        order = np.argsort(-scores)
        sorted_encoded = encoded[order]
        unique, indices = np.unique(sorted_encoded, axis=0, return_index=True)
        elite = sorted_encoded[np.sort(indices)[:96]]
        encoded = elite[generator.integers(0, len(elite), population)].copy()
        locations = generator.integers(0, 64, size=(population, 2))
        for index in range(population):
            first, second = sorted(locations[index])
            move = generator.integers(0, 6)
            if move == 0:
                encoded[index, first] = generator.integers(0, 3)
            elif move == 1:
                encoded[index, first], encoded[index, second] = encoded[index, second], encoded[index, first]
            elif move == 2:
                encoded[index, first:second + 1] = np.roll(encoded[index, first:second + 1], 1)
            elif move == 3:
                encoded[index, first:second + 1] = np.roll(encoded[index, first:second + 1], -1)
            elif move == 4:
                encoded[index, first:second + 1] = encoded[index, first:second + 1][::-1]
            else:
                parent = elite[generator.integers(0, len(elite))]
                encoded[index, first:second + 1] = parent[first:second + 1]
        encoded[:len(elite)] = elite
    return best_word


def main():
    started = time.monotonic()
    deadline = started + 600
    try:
        cores = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {cores[-min(6, len(cores))]})
    except (AttributeError, OSError):
        pass
    counts = {"probability_batch_calls": 0, "circuit_scenario_evaluations": 0, "independent_evaluator_calls": 0,
              "completed_parameter_searches": 0}
    original = search.SCREEN.probabilities

    def counted(parameters, encoded):
        counts["probability_batch_calls"] += 1
        counts["circuit_scenario_evaluations"] += len(encoded)
        return original(parameters, encoded)

    search.SCREEN.probabilities = counted
    generator = np.random.default_rng(836512)
    seed = json.loads((search.OUTPUT / "worker_0_best_witness.json").read_text())
    best = search.EVALUATOR.score_witness(seed)
    counts["independent_evaluator_calls"] += 1
    best_witness = seed
    history = []
    search.save("reorder_best_witness.json", best_witness)
    search.save("reorder_best_evaluation.json", best)
    try:
        cycle = 0
        while time.monotonic() < deadline:
            parameters = np.array(best_witness["gate_parameters"]).ravel()
            word = best_witness["circuit"]
            if cycle % 3 == 2:
                parameters.reshape(3, 5)[:, 0] += generator.normal(0, .02, 3)
            word = explore(parameters, word, generator, deadline)
            candidate, measured, success, evaluations = search.optimize_parameters(parameters, word, 1, deadline)
            counts["completed_parameter_searches"] += 1
            witness = {"version": 1, "gate_parameters": candidate.reshape(3, 5).tolist(), "circuit": word}
            result = search.EVALUATOR.score_witness(witness)
            counts["independent_evaluator_calls"] += 1
            record = {"cycle": cycle, "optimizer_function_evaluations": evaluations, "solver_success": success,
                      "core_score": result["core_score"], "worst_family_score": result["worst_family_score"],
                      "passed": result["passed"], "margins": search.margins(result), "seconds": time.monotonic() - started}
            history.append(record)
            search.save("reorder_history.json", history)
            print(json.dumps(record), flush=True)
            if search.feasible(result) and result["worst_family_score"] > best["worst_family_score"]:
                best = result
                best_witness = witness
                search.save("reorder_best_witness.json", best_witness)
                search.save("reorder_best_evaluation.json", best)
            if result["passed"]:
                break
            cycle += 1
    except TimeoutError:
        pass
    search.save("reorder_summary.json", {"runtime_seconds": time.monotonic() - started, "counts": counts,
                                          "core_score": best["core_score"], "worst_family_score": best["worst_family_score"],
                                          "passed": best["passed"], "margins": search.margins(best)})


if __name__ == "__main__":
    main()
