import json
from pathlib import Path

from sandbox import run_submission


root = Path(__file__).resolve().parents[1]
paths = [str(root / "concept_2/evaluator/hidden/seeds.json"),
         str(root / "concept_2/adversary/baseline_score.json"),
         "/home/xuandong/.codex/config.toml", "/srv/home/xuandong/.codex/config.toml"]
result, resources = run_submission(root / "authoring/isolation_probe", {"forbidden_paths": paths}, timeout=60)
assert not any(result["forbidden_readable"].values())
assert not result["network"]
assert not result["affinity_change"]
assert abs(result["eigenvalues"][0] - 0.5) < 1e-12
report = {"passed": True, "result": result, "resource": resources}
(root / "authoring/isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report), flush=True)
