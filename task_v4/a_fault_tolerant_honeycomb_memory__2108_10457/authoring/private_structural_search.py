import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"
DESTINATION = CONCEPT / "adversary/private_dense_portfolio"
sys.path.insert(0, str(CONCEPT / "evaluator"))
from evaluate import evaluate


candidates = {}
counts = {}
for stem in ["matchings", "neighbors"]:
    subprocess.run([sys.executable, str(CONCEPT / "attempts/v_1" / (stem + ".py"))],
                   cwd=DESTINATION, check=True)
    patterns = DESTINATION / (stem + ".txt")
    counts[stem] = len(patterns.read_text().splitlines())
    with (DESTINATION / (stem + "_dense.log")).open("w") as stream:
        subprocess.run([str(DESTINATION / "optimizer"), str(DESTINATION / "train_0.bin"),
                        "scan", str(patterns)], stdout=stream, check=True, timeout=600)
    for line in (DESTINATION / (stem + "_dense.log")).read_text().splitlines():
        fields = line.split()
        if not fields or fields[0] != "SCORE":
            continue
        candidates[fields[1]] = {"core": float(fields[3]), "worst": float(fields[4]), "origin": stem}
ordered = sorted(candidates, key=lambda pattern: (min(candidates[pattern]["core"] - 0.85,
                                                     candidates[pattern]["worst"] - 0.60),
                                                 candidates[pattern]["core"]), reverse=True)
records = []
for index, pattern in enumerate(ordered[:12]):
    path = DESTINATION / f"structural_{index}.json"
    path.write_text(json.dumps({"z_image": list(map(int, pattern))}) + "\n")
    result = evaluate(path)
    records.append({"pattern": pattern, "training": candidates[pattern], "score": result,
                    "artifact": str(path.relative_to(CONCEPT))})
    print(pattern, result["core_score"], result["worst_family_score"], result["passed"], flush=True)
report = {"structural_candidates": counts, "unique_candidates": len(candidates),
          "full_frozen_evaluations": records,
          "known_passing_solution": any(record["score"]["passed"] for record in records),
          "note": "All 116 native perfect matchings plus the previous agent's two-edit neighborhoods. This is not an exhaustive search of all 3^24 designs and does not prove impossibility."}
(DESTINATION / "structural_report.json").write_text(json.dumps(report, indent=2) + "\n")
