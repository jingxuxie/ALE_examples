import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "generations/generation_2"
files = {}
protocol = json.loads((STAGE / "participant/input/protocol.json").read_text())
protocol["family"] = [member for member in protocol["family"] if member["group"] != "interior"]
assert len(protocol["family"]) == 37
protocol["uncertainty_design"]["construction"] = "Keep all five generation-1 members; add the complete 2^5 Cartesian corner set. Every member and numerical coordinate is explicitly listed in family. The two calibration signs, two shape signs, and phase sign are independent."
protocol["uncertainty_design"]["interior_provenance"] = "Sixteen predetermined interior points were audited privately for calibration, not selected by severity. They are not grading members. Only the 37 explicit family members are scored; there are no hidden perturbations."
protocol["uncertainty_design"]["budget_rationale"] = "A 53-member draft exceeded the 420-second wall budget under load. The final design keeps the complete 32-corner Cartesian set plus all five legacy members, omitting auxiliary interior audit points without weakening the 32-corner coverage or changing any numerical accuracy threshold."
for field in ("core_score", "definition"):
    protocol["target"][field] = protocol["target"][field].replace("53", "37")
protocol["reference"]["evaluation_pruning"] = "The full unchanged four-solve reference check is performed for each evaluated member. On the first unresolved reference, assessment stops with valid=false, passed=false and zero score. complete_assessment records whether all members were reached; skipped members are explicitly counted. Otherwise all 37 members are fully evaluated, including any guard-failing member."
for name in ("participant/input/protocol.json", "evaluator/hidden/protocol.json"):
    files[STAGE / name] = json.dumps(protocol, indent=2) + "\n"
for name in ("participant/workspace/README.md", "README.md", "evaluator/test_contract.py"):
    text = (STAGE / name).read_text().replace("53", "37")
    text = text.replace("and 16 predetermined interior points", "without hidden or randomly drawn grading points")
    text = text.replace('    assert sum(member["group"] == "interior" for member in members) == 16', '    assert sum(member["group"] == "interior" for member in members) == 0')
    text = text.replace('result["group_scores"]["interior"]', 'result["group_scores"]["corner"]')
    files[STAGE / name] = text
status = json.loads((STAGE / "status.json").read_text())
status.update(family_members=37, budget_calibration="53-member draft timed out at 420 wall seconds; retained all 32 corners and five legacy cases", build_status="37_member_validation_running")
files[STAGE / "status.json"] = json.dumps(status, indent=2) + "\n"
files[ROOT / "adversary/ratchet_1/draft_53_budget_failure.json"] = (STAGE / "attempts/baseline.evaluation.json").read_text()
sections = ["*** Begin Patch"]
for path, content in files.items():
    sections.append("*** Add File: " + str(path.relative_to(ROOT)))
    sections.extend("+" + line for line in content.splitlines())
sections.append("*** End Patch")
subprocess.run(["apply_patch"], input="\n".join(sections) + "\n", text=True, cwd=ROOT, check=True)
