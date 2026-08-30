import argparse
import json
import time

from harness import ROOT, load_mps, measure, sha256, write_json
from refine import project_parity
from trusted_contractor import save_mps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--source-case", required=True)
    parser.add_argument("--source-label", default="v4_40")
    args = parser.parse_args()
    request_path = ROOT / "requests" / (args.case + ".json")
    source_request_path = ROOT / "requests" / (args.source_case + ".json")
    request = json.loads(request_path.read_text())
    source_request = json.loads(source_request_path.read_text())
    source_path = ROOT / "runs" / args.source_case / args.source_label / "state.npz"
    source = load_mps(source_path, source_request)
    started = time.process_time()
    wall_started = time.monotonic()
    compressed = project_parity(source, request, request["sector"])
    directory = ROOT / "runs" / args.case / "compressed_seed"
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / "state.npz"
    save_mps(state_path, compressed)
    checked = measure(load_mps(state_path, request), request)
    record = {
        "method": "Exact parity projection followed by charge-resolved Schmidt truncation to target cap",
        "target_request_sha256": sha256(request_path), "source_request_sha256": sha256(source_request_path),
        "source_request": str(source_request_path.relative_to(ROOT)),
        "source_state": str(source_path.relative_to(ROOT)), "source_state_sha256": sha256(source_path),
        "source_bond_cap": source_request["bond_cap"], "final_bond_cap": request["bond_cap"],
        "measurement_uses_target_hamiltonian": True, "measurement": checked,
        "state_sha256": sha256(state_path), "state_bytes": state_path.stat().st_size,
        "compression_cpu_seconds": time.process_time() - started,
        "compression_wall_seconds": time.monotonic() - wall_started,
        "ground_energy_certified": False,
    }
    write_json(directory / "seed_measurement.json", record)
    print(json.dumps({"case_id": args.case, **checked}), flush=True)


if __name__ == "__main__":
    main()
