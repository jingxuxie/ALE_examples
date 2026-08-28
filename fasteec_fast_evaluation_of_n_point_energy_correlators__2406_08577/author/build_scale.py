import json
from pathlib import Path

from build_pilots import AUTHOR, CONCEPTS, ROOT, queries, reference


def main():
    for kind in CONCEPTS:
        directory = ROOT / "pilots" / kind / "private" / "challenge_pool" / "pilot_full_sample_scale"
        directory.mkdir(parents=True, exist_ok=True)
        data = directory / "events.txt"
        if not data.exists():
            data.symlink_to(AUTHOR / "cms100k.txt")
        query = queries(kind)[1] if kind == "weighted" else queries(kind)[0]
        if kind == "fractional":
            query = dict(log_min=-4.0, bins=48, nu=0.35, nsub=8)
        if kind == "resolved":
            query = dict(log_min=-4.0, bins=48, order=3, ratio_bins=6, phi_bins=8)
        job = {"kind": kind, "events_file": "events.txt", "nevents": 100000, "queries": [query]}
        (directory / "job.json").write_text(json.dumps(job, indent=2))
        manifest_path = directory.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["cases"] = [case for case in manifest["cases"] if case["id"] != directory.name]
        manifest["cases"].append({"id": directory.name, "family": "full_sample_scale", "split": "pilot", "nevents": 100000, "max_constituents": 139, "source_ids": "entire unmodified 100000-jet release asset", "independent_generalization_case": False})
        manifest["scale_note"] = "The full-asset throughput case intentionally overlaps statistical strata; it is not counted as independent heldout generalization. Per-case pool and heldout outcomes use disjoint groups and different queries where ratcheted."
        manifest_path.write_text(json.dumps(manifest, indent=2))
        reference(kind, directory.name)


if __name__ == "__main__":
    main()
