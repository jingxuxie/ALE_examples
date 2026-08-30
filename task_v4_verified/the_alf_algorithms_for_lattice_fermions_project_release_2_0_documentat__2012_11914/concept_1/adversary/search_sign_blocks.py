import argparse
import json
import time
from pathlib import Path

import numpy as np

from search_sign import SignObjective
from search_sign_deep import StencilObjective


def run(arguments):
    seeds = [np.asarray(json.loads(path.read_text())["fields"], dtype=np.int8) for path in arguments.start]
    physical = SignObjective(arguments.beta, 4.0, 1.0, 16, 0.0)
    stencil = StencilObjective(arguments.beta)
    random = np.random.default_rng(651190)
    start = time.monotonic()
    count = 0
    nominal_negative = 0
    found = False
    for location in random.permutation(16):
        horizontal, vertical = divmod(int(location), 4)
        sites = [4 * ((horizontal + delta_horizontal) % 4) + (vertical + delta_vertical) % 4 for delta_horizontal, delta_vertical in [(0, 0), (0, 1), (1, 1), (1, 0)]]
        for seed_index, fields in enumerate(seeds):
            for offset in range(0, 65536, 256):
                if time.monotonic() - start > arguments.seconds:
                    break
                patterns = (((np.arange(offset, offset + 256)[:, None] >> np.arange(16)[None]) & 1) * 2 - 1).astype(np.int8)
                candidates = np.repeat(fields[None], 256, axis=0)
                for phase in range(4):
                    for site_index, site in enumerate(sites):
                        candidates[:, phase * 4:(phase + 1) * 4, site] = patterns[:, phase * 4 + site_index, None]
                products = physical.products(candidates)
                signs = np.linalg.slogdet(np.eye(16) + np.exp(arguments.beta) * products)[0].prod(axis=1)
                negative = np.flatnonzero(signs < 0)
                count += len(candidates)
                nominal_negative += len(negative)
                if len(negative):
                    scores = stencil.evaluate(candidates[negative], "product")
                    selected = int(np.argmin(scores))
                    if scores[selected] < -1e-14:
                        record = stencil.record(candidates[negative[selected]], "product", float(scores[selected]), time.monotonic() - start, count, 651190)
                        record["search_method"] = "enumerated four-time-block plaquette fields"
                        arguments.output.write_text(json.dumps(record, indent=2) + "\n")
                        arguments.output.with_name(arguments.output.stem + "_fields.json").write_text(json.dumps({"fields": record["fields"]}) + "\n")
                        print(json.dumps({"block_witness_saved": str(arguments.output), "beta": arguments.beta, "count": count, "seconds": time.monotonic() - start}), flush=True)
                        found = True
                        break
            print(json.dumps({"block_location": int(location), "seed_index": seed_index, "count": count, "nominal_negative": nominal_negative, "seconds": time.monotonic() - start}), flush=True)
            if found or time.monotonic() - start > arguments.seconds:
                break
        if found or time.monotonic() - start > arguments.seconds:
            break
    summary = {"found": found, "beta": arguments.beta, "count": count, "nominal_negative": nominal_negative, "seconds": time.monotonic() - start}
    arguments.output.with_name(arguments.output.stem + "_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--beta", type=float, default=0.75)
    parser.add_argument("--seconds", type=float, default=60)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
