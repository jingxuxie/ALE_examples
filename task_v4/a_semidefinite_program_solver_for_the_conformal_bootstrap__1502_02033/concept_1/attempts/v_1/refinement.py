import json
from pathlib import Path

import solution
from benchmark import run


original_minimize = solution.minimize


def extended_minimize(*args, **kwargs):
    if kwargs.get("method") == "SLSQP":
        kwargs["options"] = dict(kwargs["options"], maxiter=600)
    return original_minimize(*args, **kwargs)


if __name__ == "__main__":
    solution.minimize = extended_minimize
    for filename in ("stress_damping_48.json", "stress_pole_count_48.json", "stress_clusters_48.json", "random_6.json", "random_10.json", "random_25.json"):
        original = json.loads(Path(filename).read_text())
        result = run(original["data"], "refined_" + original["name"])
        result["previous_log_loss"] = original["log_loss"]
        Path("refined_" + filename).write_text(json.dumps(result))
