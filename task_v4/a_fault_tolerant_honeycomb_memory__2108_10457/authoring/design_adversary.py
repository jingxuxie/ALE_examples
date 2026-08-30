import argparse
import json
import math
from pathlib import Path
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "concept_2/evaluator"))
from design_common import ambiguity, load_case, read_design, selected_columns


def profiles():
    result = []
    for density in [0.12, 0.18, 0.24, 0.30, 0.40, 0.50]:
        result.append({"name": f"iid_{density}", "kind": "iid", "density": density})
    for density in [0.08, 0.12, 0.16, 0.20, 0.24, 0.30]:
        result.append({"name": f"persistent_{density}", "kind": "persistent", "density": density})
    for slope in [(1, 0), (0, 1), (1, 1), (1, -1), (2, 1), (1, 2)]:
        for persistent in [False, True]:
            result.append({"name": f"band_{slope[0]}_{slope[1]}_{int(persistent)}", "kind": "band",
                           "slope": list(slope), "width": 0.20, "inside": 0.80,
                           "outside": 0.01, "persistent": persistent})
    for phase in range(3):
        result.append({"name": f"paired_phase_{phase}", "kind": "paired_phase", "phase": phase,
                       "density": 0.48})
    return result


def supports(case, profile, seed, count):
    generator = random.Random(seed)
    positions = case["data_coordinates"]
    qubits = len(positions)
    rounds = case["noisy_subrounds"]
    width, height = case["coordinate_period"]
    result = []
    for repeat in range(count):
        origin = generator.random()
        if profile["kind"] == "band":
            horizontal_slope, vertical_slope = profile["slope"]
            probabilities = [profile["inside"] if (horizontal_slope * horizontal / width +
                             vertical_slope * vertical / height - origin) % 1 < profile["width"]
                             else profile["outside"] for horizontal, vertical in positions]
        else:
            probabilities = [profile["density"]] * qubits
        persistent = profile["kind"] == "persistent" or profile.get("persistent", False)
        if persistent:
            active = [qubit for qubit, probability in enumerate(probabilities) if generator.random() < probability]
            selected = [subround * qubits + qubit for subround in range(rounds) for qubit in active]
        else:
            selected = []
            for subround in range(rounds):
                if profile["kind"] == "paired_phase" and subround % 3 != profile["phase"]:
                    continue
                selected.extend(subround * qubits + qubit for qubit, probability in enumerate(probabilities)
                                if generator.random() < probability)
        result.append(selected)
    return result


def score(columns, records):
    amounts = [ambiguity(columns[index] for index in support) for support in records]
    return {"correct": sum(amount == 0 for amount in amounts), "count": len(amounts),
            "fraction": sum(amount == 0 for amount in amounts) / len(amounts),
            "mean_ambiguity": sum(amounts) / len(amounts),
            "mean_flags": sum(map(len, records)) / len(records),
            "failed_indices": [index for index, amount in enumerate(amounts) if amount][:3]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=128)
    arguments = parser.parse_args()
    axes = read_design(arguments.design)
    definitions = profiles()
    reports = []
    started = time.monotonic()
    for scale in [1, 2, 3]:
        case = load_case(ROOT / f"concept_2/participant/input/scale_{scale}.json.gz")
        columns = selected_columns(case, axes)
        for profile_index, profile in enumerate(definitions):
            records = supports(case, profile, 281901 + 7307 * scale + 107 * profile_index, arguments.count)
            report = score(columns, records)
            report.update({"scale": scale, "profile": profile,
                           "examples": [records[index] for index in report.pop("failed_indices")]})
            reports.append(report)
            print(scale, profile["name"], report["fraction"], round(report["mean_flags"], 1), flush=True)
    result = {"design": axes, "reports": reports, "supports": sum(report["count"] for report in reports),
              "seconds": time.monotonic() - started,
              "interpretation": "Private physically defined lab-Z erasure profiles. Persistent flags correlate locations across time but each unknown error bit is independent in the exact worst-case certificate. Closed bands wrap consistently on the torus. Most persistent and band profiles have global flag density comparable to original IID cases. Generation1 targets are unchanged."}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
