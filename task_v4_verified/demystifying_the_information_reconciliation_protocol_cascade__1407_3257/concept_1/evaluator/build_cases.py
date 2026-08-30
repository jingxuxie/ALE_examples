import json
import random
import secrets
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant"))
from baseline import baseline_policy
from cascade_sim import stable_seed
FAMILIES = {
    "bandwidth": {"sizes": [1024, 2048, 4096], "rates": [0.004, 0.012, 0.028, 0.055],
                  "biases": [0.4, 0.7, 1.0, 1.7], "samples": [96, 256, 768], "latencies": [0.0002, 0.0005, 0.001]},
    "latency": {"sizes": [1024, 2048, 4096], "rates": [0.008, 0.025, 0.05, 0.08],
                "biases": [0.7, 1.0, 1.4], "samples": [128, 384, 1024], "latencies": [0.006, 0.012, 0.024]},
    "drift": {"sizes": [1024, 2048, 4096, 8192], "rates": [0.006, 0.018, 0.035, 0.07],
              "biases": [0.3, 0.5, 1.8, 2.4], "samples": [128, 512, 1024], "latencies": [0.001, 0.003, 0.008]},
    "short_frame": {"sizes": [512, 1024, 2048], "rates": [0.0015, 0.004, 0.012, 0.035, 0.07],
                    "biases": [0.5, 1.0, 1.8], "samples": [64, 128, 256], "latencies": [0.001, 0.004, 0.012]},
}


def write_json(relative, data):
    contents = json.dumps(data, indent=2) + "\n"
    patch = f"*** Begin Patch\n*** Add File: {ROOT / relative}\n" + "".join("+" + line + "\n" for line in contents.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def main():
    if (ROOT / "evaluator/frozen.json").exists():
        raise RuntimeError("refusing to regenerate frozen cases")
    used_tuples = set()
    used_seeds = set()
    for split, master_seed, case_count, frames in [("train", 1407325701, 8, 8), ("dev", 1407325702, 12, 32),
                                                  ("hidden", secrets.randbits(128), 16, 64)]:
        generator = random.Random(master_seed)

        def next_seed():
            while True:
                seed = generator.randrange(1, 2 ** 63)
                if seed not in used_seeds:
                    used_seeds.add(seed)
                    return seed

        cases = []
        for family, grid in FAMILIES.items():
            for unused in range(case_count):
                while True:
                    values = tuple(generator.choice(grid[field]) for field in ["sizes", "rates", "biases", "samples", "latencies"])
                    if values not in used_tuples:
                        used_tuples.add(values)
                        break
                frame_bits, rate, bias, sample_size, latency = values
                cases.append({"family": family, "frame_bits": frame_bits, "q_true": rate,
                              "estimate_bias": bias, "sample_size": sample_size, "latency": latency,
                              "frame_seeds": [next_seed() for unused_frame in range(frames)]})
        stress = []
        for frame_bits in [512, 2048, 8192]:
            stress_count = {"train": 24, "dev": 64, "hidden": 256}[split]
            frame_seeds = [next_seed() for unused_frame in range(stress_count)]
            errors = []
            for frame_index, frame_seed in enumerate(frame_seeds):
                sample_source = random.Random(stable_seed(frame_seed, "estimate"))
                sample_errors = sum(sample_source.random() < 0.006 for unused_sample in range(256))
                estimate = min(0.15, max(1 / frame_bits, (sample_errors + 0.5) / 257))
                import math
                alpha = math.log2(1 / estimate) - 0.5
                first_size = min(frame_bits // 2, max(2, 2 ** math.ceil(alpha)))
                second_size = min(frame_bits // 2, max(2, 2 ** math.ceil((alpha + math.log2(frame_bits / 4)) / 2)))
                memberships = []
                for pass_index, size in enumerate([first_size, second_size]):
                    permutation = list(range(frame_bits))
                    random.Random(stable_seed(frame_seed, f"permutation:{pass_index}")).shuffle(permutation)
                    membership = [0] * frame_bits
                    for position, bit in enumerate(permutation):
                        membership[bit] = position // size
                    memberships.append(membership)
                buckets = {}
                for bit in range(frame_bits):
                    bucket = (memberships[0][bit], memberships[1][bit])
                    buckets.setdefault(bucket, []).append(bit)
                count = 2 if frame_index % 3 else 4
                eligible = [bits for bits in buckets.values() if len(bits) >= count]
                errors.append(sorted(generator.sample(generator.choice(eligible), count)))
            stress.append({"family": "pair_stress", "frame_bits": frame_bits, "q_true": 0.006,
                           "estimate_bias": 1.0, "sample_size": 256, "latency": 0.003,
                           "frame_seeds": frame_seeds, "errors": errors})
        relative = "evaluator/hidden/cases.json" if split == "hidden" else f"participant/inputs/{split}.json"
        write_json(relative, {"version": 1, "split": split, "cases": cases, "stress": stress})
    write_json("participant/inputs/distribution.json", FAMILIES)
    write_json("participant/policy.json", baseline_policy())
    write_json("champions/baseline/policy.json", baseline_policy())


if __name__ == "__main__":
    main()
