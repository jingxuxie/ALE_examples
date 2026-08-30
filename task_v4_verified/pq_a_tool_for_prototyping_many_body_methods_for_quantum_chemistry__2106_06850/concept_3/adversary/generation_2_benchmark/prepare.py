"""Prepare only allowlisted completed-champion code and public target inputs."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
CHAMPION = CONCEPT / "champions" / "generation_1"
SNAPSHOT = CONCEPT / "adversary" / "generation_1_snapshot" / "participant"
POOL = CONCEPT / "adversary" / "candidate_pool"


def save_texts(files):
    patch = "*** Begin Patch\n"
    for relative, content in files.items():
        path = ROOT / relative
        if path.exists():
            raise RuntimeError("refusing to overwrite prepared benchmark file: " + relative)
        patch += "*** Add File: " + str(path) + "\n"
        patch += "".join("+" + line + "\n" for line in content.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def main():
    files, provenance = {}, {}
    old_path = "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/pq_a_tool_for_prototyping_many_body_methods_for_quantum_chemistry__2106_06850/concept_3/participant/workspace"
    for name in ("explore.py", "assemble.py", "continuous.py", "refine.py", "bridges.py", "export_data.py", "beam.cpp", "model.cpp"):
        original = (CHAMPION / name).read_text()
        content = original.replace(old_path, "/runtime/workspace")
        content = content.replace("load_cases()[1]", "load_cases()[0]")
        files["runtime/champion/" + name] = content
        provenance[name] = {"source_sha256": hashlib.sha256(original.encode()).hexdigest(),
                            "adapted_sha256": hashlib.sha256(content.encode()).hexdigest(),
                            "changes": "only fixed import path and single-case input index" if content != original else "none"}
    original = (SNAPSHOT / "workspace" / "fermion.py").read_text()
    engine = original.replace('Path(__file__).resolve().parents[1] / "input" / "targets.json"', 'Path("/work/targets.json")')
    engine = engine.replace('len(data["cases"]) != 3', 'len(data["cases"]) != 1')
    engine = engine.replace("exactly three targets are required", "exactly one benchmark target is required")
    engine = engine.replace('integers["max_gates"] <= 20', 'integers["max_gates"] <= 32')
    files["runtime/workspace/fermion.py"] = engine
    files["runtime/workspace/baseline.py"] = (SNAPSHOT / "workspace" / "baseline.py").read_text()
    catalog = []
    old_targets = json.loads((SNAPSHOT / "input" / "targets.json").read_text())
    new_targets = json.loads((POOL / "targets.json").read_text())
    for group, document in (("control", old_targets), ("pool", new_targets)):
        for case in document["cases"]:
            identifier = group + "_" + case["case_id"]
            payload = {"schema_version": 1, "fidelity_threshold": 0.999999999, "cases": [case]}
            content = json.dumps(payload, indent=2, allow_nan=False) + "\n"
            files["inputs/" + identifier + "/targets.json"] = content
            catalog.append({"id": identifier, "group": group, "case_id": case["case_id"],
                            "n_orbitals": case["n_orbitals"], "n_electrons": case["n_electrons"], "max_gates": case["max_gates"],
                            "target_sha256": hashlib.sha256(content.encode()).hexdigest()})
    files["catalog.json"] = json.dumps({"cases": catalog}, indent=2) + "\n"
    save_texts(files)
    for name in ("beam3", "model.so"):
        source, destination = CHAMPION / name, ROOT / "runtime" / "champion" / name
        shutil.copyfile(source, destination)
        destination.chmod(0o755)
        provenance[name] = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                            "adapted_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "changes": "none; original archived binary"}
    save_texts({"source_provenance.json": json.dumps({
        "archived_champion_only": True, "no_archived_inputs_outputs_or_seeds_copied": True,
        "algorithm_changes": False, "files": provenance,
        "runtime_engine_changes": ["single public input case", "explicit /work target path", "loader gate cap 32"],
    }, indent=2) + "\n"})
    print(json.dumps({"prepared_cases": len(catalog), "controls": 3, "pool_cases": len(catalog) - 3}), flush=True)


if __name__ == "__main__":
    main()
