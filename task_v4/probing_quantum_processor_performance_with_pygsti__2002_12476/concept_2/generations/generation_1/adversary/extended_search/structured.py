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
    counts = {"probability_batch_calls": 0, "circuit_scenario_evaluations": 0, "independent_evaluator_calls": 0}
    original = search.SCREEN.probabilities

    def counted(parameters, encoded):
        counts["probability_batch_calls"] += 1
        counts["circuit_scenario_evaluations"] += len(encoded)
        return original(parameters, encoded)

    search.SCREEN.probabilities = counted
    seed = json.loads((search.OUTPUT / "worker_0_best_witness.json").read_text())
    parameters = np.asarray(seed["gate_parameters"]).ravel()
    candidates = set()
    for first_count in range(15):
        for second_count in range(15):
            for first_pulse in ["XX", "XXXX", "YY", "YYYY", "XYXYXY"]:
                for second_pulse in ["XX", "XXXX", "YY", "YYYY", "XYXYXY"]:
                    block = "I" * first_count + first_pulse + "I" * second_count + second_pulse
                    for preparation in ["X", "Y", "XXX", "YYY"]:
                        for measurement in ["X", "Y", "XXX", "YYY"]:
                            body_length = 64 - len(preparation) - len(measurement)
                            repetitions, remainder = divmod(body_length, len(block))
                            for placement in [0, 1]:
                                body = block * repetitions + "I" * remainder if placement else "I" * remainder + block * repetitions
                                word = preparation + body + measurement
                                if min(word.count(symbol) for symbol in "IXY") >= 4:
                                    candidates.add(word)
    words = sorted(candidates)
    ranks = []
    for start in range(0, len(words), 1024):
        chunk = words[start:start + 1024]
        results = search.SEARCH.data(parameters, search.SCREEN.encode(chunk))
        scores = np.min([abs(residual) for residual, leakage in results], axis=0)
        scores -= 5 * np.maximum(np.max([leakage for residual, leakage in results], axis=0) - .0098, 0)
        ranks.extend((float(score), word) for score, word in zip(scores, chunk))
    ranks.sort(reverse=True)
    selected = []
    for score, word in ranks:
        if all(sum(first != second for first, second in zip(word, previous)) > 14 for previous in selected):
            selected.append(word)
        if len(selected) >= 6:
            break
    search.save("structured_ranked_words.json", {"candidates": len(words), "top_scores": ranks[:24], "selected": selected})
    best = search.EVALUATOR.score_witness(seed)
    counts["independent_evaluator_calls"] += 1
    best_witness = seed
    history = []
    try:
        for index, word in enumerate(selected):
            candidate, measured, success, evaluations = search.optimize_parameters(parameters, word, 1, deadline)
            witness = {"version": 1, "gate_parameters": candidate.reshape(3, 5).tolist(), "circuit": word}
            result = search.EVALUATOR.score_witness(witness)
            counts["independent_evaluator_calls"] += 1
            record = {"index": index, "solver_success": success, "optimizer_function_evaluations": evaluations,
                      "core_score": result["core_score"], "worst_family_score": result["worst_family_score"],
                      "passed": result["passed"], "margins": search.margins(result), "seconds": time.monotonic() - started}
            history.append(record)
            search.save("structured_history.json", history)
            print(json.dumps(record), flush=True)
            if search.feasible(result) and result["worst_family_score"] > best["worst_family_score"]:
                best = result
                best_witness = witness
            if result["passed"]:
                break
    except TimeoutError:
        pass
    search.save("structured_best_witness.json", best_witness)
    search.save("structured_best_evaluation.json", best)
    search.save("structured_summary.json", {"runtime_seconds": time.monotonic() - started,
                                             "unique_structured_candidates": len(words), "counts": counts,
                                             "core_score": best["core_score"], "worst_family_score": best["worst_family_score"],
                                             "passed": best["passed"], "margins": search.margins(best)})


if __name__ == "__main__":
    main()
