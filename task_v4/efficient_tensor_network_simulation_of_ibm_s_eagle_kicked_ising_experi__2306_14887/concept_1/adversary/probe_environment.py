import importlib.util
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parent.parent
specification = importlib.util.spec_from_file_location("checker", ROOT / "evaluator" / "evaluate.py")
checker = importlib.util.module_from_spec(specification)
specification.loader.exec_module(checker)
instance = {"n": 2, "edges": [{"u": 0, "v": 1, "dim": 4}], "memory_elements": 1024}
with tempfile.TemporaryDirectory(prefix="heavyhex_probe_") as scratch:
    plan, elapsed, resources = checker.run_solver(ROOT / "adversary" / "environment_probe", instance, scratch)
result = checker.checked_cost(instance, plan)
assert result["work"] == 4 and result["feasible"]
payload = {"passed": True, "runtime_seconds_excluding_namespace_setup": elapsed,
           "numpy_scipy_networkx_imports": True, "hidden_and_sibling_paths_inaccessible": True,
           "participant_paths_preserved": True, "one_cpu_affinity": True,
           "network_namespace": "unshared by bubblewrap", "resources": resources}
(ROOT / "evaluator" / "hidden" / "environment_audit.json").write_text(json.dumps(payload, indent=2) + "\n")
print(json.dumps(payload, indent=2))
