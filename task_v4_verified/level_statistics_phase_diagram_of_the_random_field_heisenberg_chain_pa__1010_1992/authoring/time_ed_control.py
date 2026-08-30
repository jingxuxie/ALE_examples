import json
import math
from pathlib import Path

from sandbox import run_submission


root = Path(__file__).resolve().parents[1]
source = root / "concept_1/participant/input/validation.jsonl"
cases = [json.loads(line) for line in source.read_text().splitlines()]
cases = (cases + cases)[:320]
cases = [{**case, "id": str(index)} for index, case in enumerate(cases)]
inputs = {"cases": [{key: case[key] for key in ("id", "L", "fields")} for case in cases]}
payload, resources = run_submission(root / "authoring/ed_control", inputs, timeout=120,
                                    streaming=True, startup_timeout=30, memory_mb=2048)
predictions = {record["id"]: record["f"] for record in payload["predictions"]}
rmse = math.sqrt(sum((predictions[case["id"]] - case["f"]) ** 2 for case in cases) / len(cases))
result = {"control": "Four-process dense exact diagonalization, warm sector construction before fields arrive",
          "records": len(cases), "lengths": {str(length): sum(case["L"] == length for case in cases) for length in (10, 12)},
          "rmse": rmse, "resource": resources, "passes_three_second_inference_limit": resources["wall_seconds"] <= 3,
          "passing_solution_for_actual_task": False}
(root / "authoring/ed_control_timing.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result), flush=True)
