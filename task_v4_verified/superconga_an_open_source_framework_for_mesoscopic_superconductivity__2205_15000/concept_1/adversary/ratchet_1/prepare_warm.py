from common import ROOT, checked_field, energy_gradient, read_case, write_json

import argparse
import hashlib
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-label", required=True)
    parser.add_argument("--destination", default="warm_cases")
    parser.add_argument("--other-labels", nargs="*", default=[])
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    destination = ROOT / args.destination
    destination.mkdir(exist_ok=True)
    provenance = []
    for metadata in read_case(ROOT / "broad_index.json"):
        name = metadata["case_id"]
        if args.only and name not in args.only:
            continue
        case = read_case(ROOT / "cases" / (name + ".json"))
        started = time.monotonic()
        path = ROOT / "runs" / args.from_label / name
        while not (path / "record.json").exists():
            if time.monotonic() - started > 300:
                raise RuntimeError("baseline did not finish")
            time.sleep(0.5)
        if not read_case(path / "record.json")["valid"]:
            raise RuntimeError("invalid baseline: " + name)
        field = checked_field(path / "field.npz", case)
        energy, unused, rms = energy_gradient(case, field)
        source = path / "field.npz"
        for label in args.other_labels:
            other_path = ROOT / "runs" / label / name
            if not (other_path / "record.json").exists() or not read_case(other_path / "record.json")["valid"]:
                continue
            other_field = checked_field(other_path / "field.npz", case)
            other_energy, unused, other_rms = energy_gradient(case, other_field)
            if other_energy < energy:
                energy, field, rms, source = other_energy, other_field, other_rms, other_path / "field.npz"
        case["initial_real"] = field.real.tolist()
        case["initial_imag"] = field.imag.tolist()
        case_path = destination / (name + ".json")
        if case_path.exists():
            raise RuntimeError("refusing to overwrite warm case")
        import json
        case_path.write_text(json.dumps(case, separators=(",", ":")) + "\n")
        provenance.append({"case_id": name, "baseline_energy": energy, "gradient_rms": rms, "source": str(source.relative_to(ROOT)), "input_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(), "contract": "supplied metastable baseline state; not private lower witness"})
    provenance_path = ROOT / (args.destination + "_provenance.json")
    previous = read_case(provenance_path) if provenance_path.exists() else []
    write_json(provenance_path, previous + provenance)


if __name__ == "__main__":
    main()
