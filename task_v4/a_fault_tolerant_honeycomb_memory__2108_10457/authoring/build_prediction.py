import collections
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
SOURCE = "https://arxiv.org/src/2108.10457v2/anc/honeycomb_memory_stats.csv"
SOURCE_SHA256 = "64fad935bfdbf8846cb68c4f3289860b34c50856ee8006f7e53672bcac1884ab"
FEATURES = ["data_width", "data_height", "rounds", "noise", "circuit_style",
            "preserved_observable", "code_distance", "num_qubits", "decoder"]


def write_csv(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    hidden = CONCEPT / "evaluator" / "hidden"
    participant = CONCEPT / "participant"
    if (CONCEPT / "evaluator" / "frozen.json").exists():
        raise RuntimeError("already frozen; refusing to regenerate a tested benchmark")
    for directory in [hidden, participant / "input", participant / "workspace",
                      CONCEPT / "attempts", CONCEPT / "champions", CONCEPT / "adversary"]:
        directory.mkdir(parents=True, exist_ok=True)
    source_path = hidden / "honeycomb_memory_stats.csv"
    if source_path.exists():
        content = source_path.read_bytes()
    else:
        with urllib.request.urlopen(SOURCE, timeout=60) as response:
            content = response.read()
    if hashlib.sha256(content).hexdigest() != SOURCE_SHA256:
        raise ValueError("original ancillary CSV hash mismatch")
    source_path.write_bytes(content)
    rows = [{key.strip(): value.strip() for key, value in row.items()}
            for row in csv.DictReader(io.StringIO(content.decode()))]
    if len(rows) != 1724 or any(row["version"] != "2" for row in rows):
        raise ValueError("unexpected source schema/version")
    seen = set()
    training, queries, labels = [], [], []
    for row in rows:
        key = tuple(row[field] for field in FEATURES)
        if key in seen:
            raise ValueError("duplicate experiment must be aggregated before splitting")
        seen.add(key)
        if row["circuit_style"] == "honeycomb_PC3":
            continue
        if int(row["rounds"]) != 3 * int(row["code_distance"]):
            raise ValueError("unexpected duration")
        if not 0 <= int(row["num_correct"]) <= int(row["num_shots"]) or int(row["num_shots"]) == 0:
            raise ValueError("invalid source counts")
        large = int(row["code_distance"]) > (11 if row["circuit_style"].startswith("surface_") else 12)
        low = float(row["noise"]) < 0.0003
        stress = "joint" if large and low else "size" if large else "noise" if low else "train"
        identifier = hashlib.sha256(("honeycomb-D-v1|" + "|".join(key)).encode()).hexdigest()[:24]
        record = {"query_id": identifier, **{field: row[field] for field in FEATURES}}
        if stress == "train":
            training.append({**record, "num_shots": int(row["num_shots"]), "num_correct": int(row["num_correct"])})
        else:
            queries.append(record)
            labels.append({**record, "stress": stress, "num_shots": int(row["num_shots"]),
                           "num_correct": int(row["num_correct"])})
    counts = collections.Counter(row["stress"] for row in labels)
    if len(training) != 780 or counts != {"size": 492, "noise": 120, "joint": 80}:
        raise ValueError("audited split counts changed")
    training.sort(key=lambda row: row["query_id"])
    queries.sort(key=lambda row: row["query_id"])
    labels.sort(key=lambda row: row["query_id"])
    write_csv(participant / "input" / "train.csv", ["query_id"] + FEATURES + ["num_shots", "num_correct"], training)
    write_csv(participant / "input" / "queries.csv", ["query_id"] + FEATURES, queries)
    (hidden / "labels.json").write_text(json.dumps(labels, indent=2) + "\n")
    protocol = json.loads((CONCEPT / "evaluator" / "protocol.json").read_text())
    (participant / "input" / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    schema = {"training": ["query_id"] + FEATURES + ["num_shots", "num_correct"],
              "query": ["query_id"] + FEATURES, "output": ["query_id", "p_failure"],
              "hidden_only": ["num_shots", "num_correct", "total_processing_seconds"],
              "query_rows": len(queries), "primary_rows": 612, "diagnostic_rows": 80}
    (participant / "input" / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    for name in ["numpy", "numpy.libs"]:
        shutil.copytree(ROOT / "authoring" / "deps" / name, participant / "workspace" / name, dirs_exist_ok=True)
    provenance = {"source": SOURCE, "sha256": SOURCE_SHA256, "bytes": len(content), "original_rows": len(rows),
                  "split_counts": {"train": len(training), **counts}, "excluded": "252 PC3 rows",
                  "built_utc": datetime.now(timezone.utc).isoformat(),
                  "labels": "unaltered original Monte Carlo counts; no baseline-generated or synthesized labels",
                  "contamination_caveat": "Public source; closed-data allowlisted evaluation prevents runtime retrieval but cannot guarantee absence of pretraining contamination. Not cryptographically hidden.",
                  "missing_configurations": "28 absent primary-grid configurations are not imputed",
                  "uncertainty": "1000:1 count-likelihood support, not fixed-n confidence coverage under adaptive stopping",
                  "baseline_before_freeze": "not run", "threshold_selection": "factor-two engineering tolerance fixed before baseline or fresh attempt"}
    (hidden / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    frozen = {"frozen_utc": datetime.now(timezone.utc).isoformat(), "sha256": {},
              "sandbox_sha256": hashlib.sha256((ROOT / "authoring" / "sandbox.py").read_bytes()).hexdigest()}
    paths = list(hidden.rglob("*")) + list((participant / "input").glob("*"))
    paths += [participant / "TASK.md", participant / "workspace" / "INTERFACE.md", CONCEPT / "evaluator" / "protocol.json",
              CONCEPT / "evaluator" / "evaluate.py", CONCEPT / "evaluator" / "scoring.py"]
    for path in sorted(paths):
        if path.is_file():
            frozen["sha256"][str(path.relative_to(CONCEPT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (CONCEPT / "evaluator" / "frozen.json").write_text(json.dumps(frozen, indent=2) + "\n")
    (CONCEPT / "evaluator" / "prediction_frozen.json").write_text(json.dumps(frozen, indent=2) + "\n")
    status = {"mode": "D", "state": "built_frozen_pending_baseline", "fresh_agent_launched": False,
              "threshold_frozen_before_attempts": True, "baseline": None,
              "split_counts": {"train": 780, "scored": 612, "diagnostic": 80},
              "champion": None, "adversary": "pending"}
    (CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"built": str(CONCEPT), "counts": status["split_counts"], "source_sha256": SOURCE_SHA256}))


if __name__ == "__main__":
    main()
