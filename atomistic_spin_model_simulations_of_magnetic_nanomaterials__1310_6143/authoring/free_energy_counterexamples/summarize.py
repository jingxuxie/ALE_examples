import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PILOT = ROOT.parents[1] / "pilots/free_energy"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inspection = json.loads((ROOT / "inspection.json").read_text())
    scouts = json.loads((ROOT / "scout_analysis.json").read_text())
    clusters = {}
    for split, payload in inspection["main_scores"].items():
        if payload["status"] != "AVAILABLE":
            clusters[split] = {"status": "PENDING"}
            continue
        scores = payload["payload"]
        families = {}
        for family, mean in scores["family_scores"].items():
            rows = [row for row in scores["cases"] if row["family"] == family]
            families[family] = {"mean_score": mean, "min_score": min(row["score"] for row in rows),
                                "case_count": len(rows), "components": {}}
            for observable in ["torque", "free_energy"]:
                components = [row["components"][observable] for row in rows]
                families[family]["components"][observable] = {
                    "mean_rmse": sum(item["rmse"] for item in components) / len(components),
                    "mean_quality": sum(item["quality"] for item in components) / len(components),
                    "baseline_normalization_count": sum(abs(item["normalization"] - item["baseline_rmse"]) < 1e-14
                                                        for item in components),
                    "uncertainty_or_absolute_floor_count": sum(item["normalization"] > item["baseline_rmse"] + 1e-14
                                                              for item in components)}
        clusters[split] = {"source": payload["path"], "sha256": digest(Path(payload["path"])),
                           "mean_score": scores["mean_score"], "worst_family_score": scores["worst_family_score"],
                           "families": families, "runtime_seconds": scores["runtime_seconds"]}
    (ROOT / "score_clusters.json").write_text(json.dumps(clusters, indent=2) + "\n")
    checks = {}
    manifest = json.loads((PILOT / "private/challenge_pool/manifest.json").read_text())
    for entries in manifest.values():
        for entry in entries:
            path = PILOT / entry["path"]
            checks[str(path)] = digest(path) == entry["sha256"]
    provenance = json.loads((ROOT / "source_provenance.json").read_text())
    for name, metadata in provenance["files"].items():
        checks[metadata["original"]] = digest(Path(metadata["original"])) == metadata["sha256"]
        checks[str(ROOT / "reference/source" / name)] = digest(ROOT / "reference/source" / name) == metadata["sha256"]
    for name, expected in scouts["protocol"]["source_hashes"].items():
        checks[str(PILOT / "attempt" / name)] = digest(PILOT / "attempt" / name) == expected
    assert all(checks.values())
    (ROOT / "immutability_checks.json").write_text(json.dumps({"all_pass": True, "checks": checks}, indent=2) + "\n")
    full_path = ROOT / "reference/results/ce_surface_compensation/full_comparison.json"
    full = json.loads(full_path.read_text()) if full_path.exists() else None
    result = {"status": "PENDING_FULL_CHECK" if full is None else full["decision"],
              "new_ratchet_built": False, "validated_counterexamples": [],
              "main_scores": {split: {key: value[key] for key in ["mean_score", "worst_family_score"] if key in value}
                              for split, value in clusters.items()},
              "deduplication": inspection["splits"],
              "source_commit": "525bc27ee44c525aee229570f30f3d4c61d54f66",
              "scouts": {name: {key: row[key] for key in ["decision", "source_max_rhat", "max_torque_combined_sem_units"]
                                if key in row} for name, row in scouts["cases"].items()},
              "full_check": full, "protected_hash_checks_pass": True,
              "limitations": ["No reduced-grid MBAR result is scored as a default-solver failure.",
                              "No scout reference is certified; only a passing full validation can certify a new reference.",
                              "Two-spin ensemble correctness does not establish large-system mixing.",
                              "No tightened score, altered ensemble, new agent, or existing-pool rerun is used."]}
    (ROOT / "STATUS.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    artifacts = {str(path.relative_to(ROOT)): digest(path) for path in sorted(ROOT.rglob("*"))
                 if path.is_file() and path.name != "ARTIFACT_HASHES.json" and "tmp" not in path.relative_to(ROOT).parts}
    (ROOT / "ARTIFACT_HASHES.json").write_text(json.dumps(artifacts, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "main_scores": result["main_scores"],
                      "protected_hash_checks_pass": True, "artifact_count": len(artifacts)}, indent=2))


if __name__ == "__main__":
    main()
