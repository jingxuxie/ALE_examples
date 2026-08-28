import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ("c01_correlated_tomography", "c02_multiscale_protection",
            "c03_resonance_compiler", "c04_colored_noise")


def main():
    runs = []
    for concept in CONCEPTS:
        directory = ROOT / "authoring" / "runs" / concept
        stages = sorted(path for path in directory.iterdir() if path.is_dir()) if directory.exists() else []
        if sum(path.name != "screening" for path in stages) > 2:
            raise RuntimeError("ratchet budget exceeded: " + concept)
        for stage in stages:
            metadata_path = stage / "result.json"
            metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else None
            if metadata is not None:
                if metadata["model"] != "ultima-alpha" or metadata["time_limit_seconds"] > 3600:
                    raise RuntimeError("pilot model or time-limit contract violated")
                if not metadata["participant_unchanged"]:
                    raise RuntimeError("participant changed during a fresh attempt")
            evaluations = {}
            for path in sorted(stage.glob("*_evaluation.json")):
                report = json.loads(path.read_text())
                evaluations[path.name.removesuffix("_evaluation.json")] = {
                    "mean_core": report["mean_core"], "worst_family": report["worst_family"],
                    "family_scores": report["family_scores"], "component_scores": report["component_scores"],
                    "case_count": len(report["cases"]), "artifact": str(path.relative_to(ROOT))}
            runs.append({"concept": concept, "stage": stage.name,
                         "status": "completed" if metadata is not None else "running",
                         "duration_seconds": metadata["elapsed_seconds"] if metadata else None,
                         "exit_code": metadata["exit_code"] if metadata else None,
                         "timed_out": metadata["timed_out"] if metadata else None,
                         "evaluations": evaluations,
                         "metadata": str(metadata_path.relative_to(ROOT)) if metadata else None})
    result = {"paper": "2001.00024", "concepts_built": len(CONCEPTS), "maximum_concepts": 4,
              "maximum_ratchets_per_concept": 2, "model": "ultima-alpha", "runs": runs,
              "interpretation": "Only completed evaluations are scores. Selection additionally requires scientific reference validation and substantive failure analysis."}
    (ROOT / "tournament_summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for run in runs:
        print(json.dumps({key: run[key] for key in ("concept", "stage", "status", "duration_seconds", "evaluations")}), flush=True)


if __name__ == "__main__":
    main()
