import hashlib
import json
import math
from pathlib import Path


def records(filename):
    result = []
    reported_loss = None
    for line in Path(filename).read_text().splitlines():
        if "Traceback" in line or "AssertionError" in line:
            raise RuntimeError(filename + " contains a failed check")
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if "loss" in record:
            reported_loss = record["loss"]
        if "ratio" in record:
            record["peak_log_error"] = abs(record["solution_log"] - reported_loss)
            assert record["peak_log_error"] < 1e-6
            assert record["ratio"] >= 0.95
            result.append(record)
    return result


def statistics(items):
    return {"cases": len(items), "minimum_improvement_ratio": min(item["ratio"] for item in items),
            "geometric_mean_improvement_ratio": math.exp(sum(math.log(item["ratio"]) for item in items) / len(items)),
            "maximum_solver_cpu": max(item["cpu"] for item in items),
            "maximum_peak_log_error": max(item["peak_log_error"] for item in items)}


if __name__ == "__main__":
    summary = {"solution_sha256": hashlib.sha256(Path("solution.py").read_bytes()).hexdigest(),
               "scope": "Independent numerical development checks; not private evaluator scores."}
    for name, filename, count in (("examples", "final_examples.log", 4), ("deterministic_stress", "final_stress.log", 21),
                                  ("random_stress", "final_random.log", 32), ("edge_stress", "final_edge.log", 18)):
        items = records(filename)
        assert len(items) == count
        summary[name] = statistics(items)
    for filename, count in (("precision_tests.log", 10), ("interface_tests.log", 8)):
        lines = Path(filename).read_text().splitlines()
        assert not any("Traceback" in line or "AssertionError" in line for line in lines)
        assert sum(line.startswith('{"name":') for line in lines) == count
    precision = json.loads(Path("precision_results.json").read_text())
    interface = json.loads(Path("interface_results.json").read_text())
    summary["precision"] = {"cases": len(precision), "maximum_log_error": max(item["high_precision_log_error"] for item in precision),
                            "maximum_gradient_relative_error": max(item["gradient_relative_error"] for item in precision)}
    summary["interface"] = {"cases": len(interface), "all_valid": all(item["valid"] for item in interface),
                            "maximum_total_process_cpu": max(item["cpu"] for item in interface),
                            "maximum_output_bytes": max(item["bytes"] for item in interface)}
    Path("validation_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
