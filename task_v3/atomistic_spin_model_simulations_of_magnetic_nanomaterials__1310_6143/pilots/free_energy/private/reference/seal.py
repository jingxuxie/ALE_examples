import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def main():
    reference=ROOT/"private/reference"
    validation=json.loads((reference/"validation.json").read_text())
    angular=json.loads((reference/"angular_refinement.json").read_text())
    independent=json.loads((reference/"independent_checks.json").read_text())
    strong=json.loads((ROOT/"private/strong_reference_scores.json").read_text())
    baseline=json.loads((ROOT/"private/baseline_cli_initial.json").read_text())
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    gates={"chain_convergence":validation["status"]=="PASS",
           "angular_convergence":angular["status"]=="PASS",
           "independent_physics":independent["status"]=="PASS",
           "strong_worst_family_above_point9":all(strong[split]["worst_family_score"]>.9 for split in manifest),
           "baseline_isolated_cli":all(item["status"]=="ok" for item in baseline["cases"]),
           "attempt_empty":not any((ROOT/"attempt").iterdir()),
           "frozen_cases":all(hashlib.sha256((ROOT/entry["path"]).read_bytes()).hexdigest()==entry["sha256"]
                              for entries in manifest.values() for entry in entries)}
    maximum_runtime=max(item["runtime_seconds"] for split in manifest for item in strong[split]["cases"])
    gates["strong_native_budget_feasible"]=maximum_runtime<600
    status={"status":"READY" if all(gates.values()) else "BLOCKED","gates":gates,
            "splits":{key:len(value) for key,value in manifest.items()},
            "max_rhat":validation["max_rhat"],"max_symmetry_z":validation["max_symmetry_z"],
            "max_angular_refinement_z":angular["max_refinement_z"],
            "max_midpoint_rhat":angular["max_midpoint_rhat"],
            "strong_means":{split:strong[split]["mean_score"] for split in manifest},
            "strong_worst_families":{split:strong[split]["worst_family_score"] for split in manifest},
            "maximum_strong_native_seconds":maximum_runtime,
            "model_agents_launched":False,"limits":"README.md: Scientific limits"}
    (ROOT/"private/BUILD_STATUS.json").write_text(json.dumps(status,indent=2)+"\n")
    hashes={}
    for folder in [ROOT/"participant",ROOT/"private"]:
        for path in sorted(folder.rglob("*")):
            relative=path.relative_to(ROOT)
            if not path.is_file() or any(part in {"vendor","__pycache__","run_scratch"} for part in relative.parts):
                continue
            if str(relative)=="private/provenance.json" or path.suffix in {".log",".pyc"}:
                continue
            hashes[str(relative)]=hashlib.sha256(path.read_bytes()).hexdigest()
    hashes["README.md"]=hashlib.sha256((ROOT/"README.md").read_bytes()).hexdigest()
    harness=ROOT.parents[1]/"authoring/isolated.py"
    provenance={"algorithm_source":"private/reference/provenance.json","files_sha256":hashes,
        "shared_isolation_harness_sha256":hashlib.sha256(harness.read_bytes()).hexdigest(),
        "compiler":"g++ -std=c++17 -O3 -DNDEBUG",
        "compiler_version":subprocess.check_output(["g++","--version"],text=True).splitlines()[0],
        "python":sys.version,"machine":platform.machine(),
        "excluded":"replaceable runtime vendor, scratch, logs, bytecode; attempt must remain empty"}
    (ROOT/"private/provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    print(json.dumps(status),flush=True)


if __name__ == "__main__":
    main()
