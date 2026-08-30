import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"
sys.path.insert(0, str(CONCEPT / "evaluator"))
from design_common import generate_supports, load_case, read_design
from evaluate import evaluate


def dataset(path, seed, count):
    with path.open("wb") as stream:
        def integer(value):
            stream.write(struct.pack("<I", value))
        integer(3)
        for case_index in range(3):
            case = load_case(CONCEPT / f"participant/input/scale_{case_index + 1}.json.gz")
            integer(len(case["columns"]))
            words = (max(value.bit_length() for triple in case["columns"] for value in triple) + 63) // 64
            if words > 7:
                raise ValueError("optimizer word capacity exceeded")
            integer(words)
            for cell, triple in zip(case["slot_cells"], case["columns"]):
                integer(cell)
                for value in triple:
                    stream.write(value.to_bytes(words * 8, "little"))
            samples = generate_supports(case, seed + case_index * 37, count, {"dense_iid": [0.28, 0.30, 0.32]})
            integer(len(samples))
            for sample in samples:
                integer(["iid_28", "iid_30", "iid_32"].index(sample["family"]))
                integer(len(sample["support"]))
                for slot in sample["support"]:
                    integer(slot)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--count", type=int, default=128)
    parser.add_argument("--seeds", type=int, default=3)
    arguments = parser.parse_args()
    destination = CONCEPT / "adversary/private_dense_portfolio"
    destination.mkdir(parents=True, exist_ok=True)
    executable = destination / "optimizer"
    source = CONCEPT / "attempts/v_1/optimize.cpp"
    subprocess.run(["g++", "-O3", "-std=c++17", str(source), "-o", str(executable)], check=True)
    starting = "".join(map(str, read_design(CONCEPT / "champions/generation_1/design.json")))
    processes = []
    streams = []
    for index in range(arguments.seeds):
        seed = 619901 + index * 4099
        data = destination / f"train_{index}.bin"
        dataset(data, seed, arguments.count)
        stream = (destination / f"search_{index}.log").open("w")
        streams.append(stream)
        command = [str(executable), str(data), "search", str(arguments.seconds), str(seed), starting]
        processes.append(subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT))
    for process in processes:
        process.wait(timeout=arguments.seconds + 120)
    for stream in streams:
        stream.close()
    patterns = {starting}
    for index in range(arguments.seeds):
        for line in (destination / f"search_{index}.log").read_text().splitlines():
            if line.startswith("FINAL "):
                patterns.add(line.split()[2])
    records = []
    for index, pattern in enumerate(sorted(patterns)):
        artifact = destination / f"design_{index}.json"
        artifact.write_text(json.dumps({"z_image": list(map(int, pattern))}) + "\n")
        result = evaluate(artifact)
        records.append({"pattern": pattern, "artifact": str(artifact.relative_to(CONCEPT)), "score": result})
        print(pattern, result["core_score"], result["worst_family_score"], result["passed"], flush=True)
    report = {"source": "prior fresh submission optimizer, reused only under generator privileges",
              "seconds_per_seed": arguments.seconds, "seeds": arguments.seeds,
              "independent_training_supports_per_group": arguments.count,
              "candidates": records, "known_passing_solution": any(record["score"]["passed"] for record in records)}
    (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
