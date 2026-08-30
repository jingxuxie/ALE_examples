from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

import shutil

from focused import digest


def main():
    destination = ROOT / "candidate_public"
    if (destination / "input/development_targets.json").exists():
        raise RuntimeError("public candidate is already assembled")
    for name in ("input/cases", "baseline", "workspace"):
        (destination / name).mkdir(parents=True, exist_ok=True)
    for name in ("MODEL.md", "SOURCES.md", "gl_model.py"):
        shutil.copyfile(CONCEPT / "participant/input" / name, destination / "input" / name)
    shutil.copyfile(ROOT / "baseline/solve.py", destination / "baseline/solve.py")
    shutil.copyfile(CONCEPT / "participant/workspace/solve.py", destination / "workspace/solve.py")
    references = read_case(ROOT / "proposal/manifest.json")
    targets = []
    mapping = {"nf03": "dev_disordered_loops", "nf06": "dev_pinned_loops"}
    for reference in references["cases"]:
        if reference["case_id"] not in mapping:
            continue
        case = read_case(ROOT / reference["case_path"])
        case["case_id"] = mapping[reference["case_id"]]
        baseline = checked_field(ROOT / reference["baseline_path"], case)
        witness = checked_field(ROOT / reference["witness_path"], case)
        baseline_energy, unused, baseline_rms = energy_gradient(case, baseline)
        witness_energy, unused, witness_rms = energy_gradient(case, witness)
        write_json(destination / "input/cases" / (case["case_id"] + ".json"), case)
        targets.append({
            "case_id": case["case_id"],
            "baseline_energy": baseline_energy,
            "witness_energy": witness_energy,
            "gap": baseline_energy - witness_energy,
            "energy_at_65_percent_gap_closure": baseline_energy - 0.65 * (baseline_energy - witness_energy),
            "baseline_gradient_rms": baseline_rms,
            "witness_gradient_rms": witness_rms,
            "baseline_kind": "exact supplied initial field, previously attained by the public champion",
            "witness_kind": "attained private portfolio field; numeric energy only is public, not a true-ground-state claim",
        })
    write_json(destination / "input/development_targets.json", {"schema_version": 1, "purpose": "public development diagnostics, excluded from hidden scoring", "cases": targets})
    write_json(ROOT / "candidate_public_manifest.json", {"status": "private draft pending main approval", "only_this_directory_may_be_published": "candidate_public", "files": {str(path.relative_to(destination)): digest(path) for path in sorted(destination.rglob("*")) if path.is_file()}, "public_baseline_sha256": digest(destination / "baseline/solve.py"), "private_witness_fields_included": False, "generator_scripts_or_seeds_included": False})


if __name__ == "__main__":
    main()
