import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import time
import zipfile

import numpy as np


SIDE = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_prediction(path, identifiers):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size <= 65536
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        assert len(entries) == 2 and sorted(entry.filename for entry in entries) == ["probabilities.npy", "query_ids.npy"]
        for entry in entries:
            assert not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            assert not stat.S_ISLNK(entry.external_attr >> 16)
            header = archive.read(entry)[:8]
            assert header[:6] == b"\x93NUMPY" and tuple(header[6:8]) in ((1, 0), (2, 0))
    with np.load(path, allow_pickle=False) as data:
        probability = data["probabilities"]
        actual_ids = data["query_ids"]
    assert probability.dtype.str == "<f8" and probability.shape == (len(identifiers), 64)
    assert actual_ids.dtype.str == "<U24" and actual_ids.shape == (len(identifiers),)
    assert probability.flags.c_contiguous and actual_ids.flags.c_contiguous
    assert np.array_equal(actual_ids, identifiers)
    assert np.isfinite(probability).all() and np.all(probability > 0) and np.all(probability <= 1)
    assert np.max(np.abs(probability.sum(axis=1) - 1)) <= 1e-10
    return probability / probability.sum(axis=1, keepdims=True)


def main():
    started = time.monotonic()
    assert (SIDE / "OUTPUTS_FROZEN.json").exists()
    assert not (SIDE / "SCORING_STARTED.json").exists()
    frozen = json.loads((SIDE / "OUTPUTS_FROZEN.json").read_text())
    protocol = json.loads((SIDE / "PREREGISTRATION.json").read_text())
    for relative, expected in frozen["files_sha256"].items():
        assert digest(SIDE / relative) == expected, relative
    assert frozen["cold_truth_opened"] is False and frozen["hidden_model_opened"] is False
    queries = json.loads((SIDE / "queries.json").read_text())
    identifiers = np.asarray([query["id"] for query in queries], dtype="<U24")
    candidates = []
    invalid = []
    for variant in protocol["variants"]:
        path = SIDE / variant["name"] / "predictions.npz"
        try:
            probability = validate_prediction(path, identifiers)
            candidates.append((variant, probability))
        except Exception as error:
            invalid.append({"name": variant["name"], "valid": False, "reason": type(error).__name__ + ":" + str(error)})
    write_json(SIDE / "SCORING_STARTED.json", {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                             "freeze_sha256": digest(SIDE / "OUTPUTS_FROZEN.json"),
                                             "all_frozen_hashes_verified": True,
                                             "valid_artifacts_before_truth_open": [variant["name"] for variant, unused in candidates]})
    truth_path = SIDE.parent / "champion1_cold_stress" / "true_probabilities.npz"
    raw = truth_path.read_bytes()
    with np.load(io.BytesIO(raw), allow_pickle=False) as cached:
        probability_keys = [key for key in cached.files if cached[key].shape == (len(queries), 64)]
        assert len(probability_keys) == 1, (cached.files, probability_keys)
        truth = np.asarray(cached[probability_keys[0]], dtype=float)
        for name in ("query_ids", "ids"):
            if name in cached.files:
                assert np.array_equal(cached[name], identifiers)
    assert np.isfinite(truth).all() and np.all(truth >= 0)
    assert np.max(np.abs(truth.sum(axis=1) - 1)) <= 1e-9
    families = sorted({query["family"] for query in queries})
    gates = protocol["frozen_gates"]
    records = []
    for variant, probability in candidates:
        kl = np.maximum(0, np.sum(truth * (np.log(np.maximum(truth, 1e-300)) - np.log(probability)), axis=1))
        tv = .5 * np.sum(np.abs(truth - probability), axis=1)
        family_kl = {family: float(np.mean(kl[[query["family"] == family for query in queries]])) for family in families}
        record = {"name": variant["name"], "valid": True, "mean_kl": float(np.mean(kl)),
                  "worst_family_kl": max(family_kl.values()), "family_kl": family_kl, "maximum_tv": float(np.max(tv)),
                  "prediction_sha256": digest(SIDE / variant["name"] / "predictions.npz"),
                  "fit_report": json.loads((SIDE / variant["name"] / "fit_report.json").read_text()),
                  "queries": [{"id": query["id"], "family": query["family"], "beta": query["beta"],
                               "kl": float(kl[index]), "tv": float(tv[index])} for index, query in enumerate(queries)]}
        record["passed"] = record["mean_kl"] <= gates["mean_kl"] and record["worst_family_kl"] <= gates["worst_family_mean_kl"] and record["maximum_tv"] <= gates["maximum_tv"]
        records.append(record)
        print(json.dumps({key: record[key] for key in ("name", "valid", "passed", "mean_kl", "worst_family_kl", "maximum_tv")}), flush=True)
    passing = [record for record in records if record["passed"]]
    best = min(passing or records, key=lambda record: record["mean_kl"]) if records else None
    report = {"query_count": len(queries), "candidate_count": len(protocol["variants"]), "valid_count": len(records),
              "passing_count": len(passing), "public_data_feasibility_established": bool(passing), "gates": gates,
              "truth_cache_sha256": hashlib.sha256(raw).hexdigest(), "queries_sha256": digest(SIDE / "queries.json"),
              "freeze_sha256": digest(SIDE / "OUTPUTS_FROZEN.json"), "single_scoring_pass": True,
              "no_score_driven_retuning": True, "hidden_model_opened": False, "records": records, "invalid": invalid,
              "best_variant": best["name"] if best else None}
    write_json(SIDE / "RESULTS.json", report)
    if best:
        for source_name, destination_name in (("predictions.npz", "best_predictions.npz"), ("fitted_parameters.npz", "best_parameters.npz")):
            source = SIDE / best["name"] / source_name
            destination = SIDE / destination_name
            assert not destination.exists()
            shutil.copyfile(source, destination)
            assert digest(source) == digest(destination)
            destination.chmod(0o444)
        write_json(SIDE / "BEST.json", {key: value for key, value in best.items() if key != "queries"})
    for relative, expected in frozen["files_sha256"].items():
        assert digest(SIDE / relative) == expected, relative
    write_json(SIDE / "SCORED_ONCE.json", {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                         "scoring_wall_seconds": time.monotonic() - started,
                                         "truth_cache_sha256": report["truth_cache_sha256"],
                                         "all_frozen_hashes_unchanged": True, "single_scoring_pass": True,
                                         "feasibility_established": bool(passing), "best_variant": report["best_variant"]})
    print(json.dumps({"finished": True, "passing_count": len(passing), "best_variant": report["best_variant"],
                      "scoring_wall_seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
