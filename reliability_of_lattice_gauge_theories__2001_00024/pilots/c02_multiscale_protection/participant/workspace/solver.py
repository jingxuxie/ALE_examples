def solve(case):
    length = case["experiment"]["length"]
    count = len(case["times"])
    return {
        "parameters": [0.1, 0.1, 0.0],
        "density": [[0.0] * length for _ in range(count)],
        "violation": [[0.0] * length for _ in range(count)],
        "correlation": [[0.0] * len(case["pairs"]) for _ in range(count)],
    }
