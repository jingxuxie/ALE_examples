import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "scratch" / "assets"


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(value)


if __name__ == "__main__":
    cases = [(path.stem, json.loads(path.read_text())) for path in sorted((ASSETS / "input").glob("*.json")) if path.name != "schema.json"]
    for filename in ("random_6.json", "random_10.json", "random_25.json", "stress_clusters_2.json"):
        record = json.loads((ROOT / filename).read_text())
        cases.append((record["name"], record["data"]))
    results = []
    with tempfile.TemporaryDirectory(prefix="interface_", dir=ROOT) as temporary:
        directory = Path(temporary)
        for name, data in cases:
            input_path = directory / "input file.json"
            output_path = directory / "output file.json"
            input_path.write_text(json.dumps(data))
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            process = subprocess.run([sys.executable, str(ROOT / "solution.py"), str(input_path), str(output_path)], cwd=directory, capture_output=True, timeout=180, preexec_fn=limits, check=True)
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            raw = output_path.read_bytes()
            output = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
            assert list(output) == ["nodes"] and len(raw) <= 65536
            nodes = output["nodes"]
            assert len(nodes) == data["degree"] + 1
            assert all(type(node) in (int, float) and math.isfinite(node) for node in nodes)
            normalized = [node * min(scenario["a"] for scenario in data["scenarios"]) for node in nodes]
            assert normalized[0] >= 0 and normalized[-1] <= 10000 * len(nodes)
            assert all(right - left > 64 * 2.0**-52 * max(1.0, right) for left, right in zip(normalized, normalized[1:]))
            assert not process.stdout
            result = {"name": name, "cpu": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, "bytes": len(raw), "valid": True}
            results.append(result)
            print(json.dumps(result), flush=True)
    (ROOT / "interface_results.json").write_text(json.dumps(results, indent=2))
