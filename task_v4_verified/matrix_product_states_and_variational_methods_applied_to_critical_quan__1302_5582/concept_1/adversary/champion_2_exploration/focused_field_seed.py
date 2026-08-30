import json
import time

from harness import ROOT, load_mps, measure, sha256, write_json
from refine import project_parity
from trusted_contractor import save_mps


def main():
    started = time.process_time()
    wall_started = time.monotonic()
    case = "f2_field_softmode"
    request_path = ROOT / "requests" / (case + ".json")
    request = json.loads(request_path.read_text())
    source_path = ROOT / "runs" / case / "v4_40/state.npz"
    state = load_mps(source_path, request)
    auxiliary = dict(request, field=[0.0] * request["n_sites"])
    records = []
    for sector in ("even", "odd"):
        projected = project_parity(state, auxiliary, sector)
        directory = ROOT / "runs" / case / ("projected_" + sector + "_seed")
        directory.mkdir(exist_ok=True)
        output = directory / "state.npz"
        save_mps(output, projected)
        checked = measure(load_mps(output, request), request)
        record = {"case_id": case, "initializer_parity": sector,
                  "refinement_sector": request["sector"], "measurement": checked,
                  "measurement_uses_full_original_nonzero_field": True,
                  "source_state_sha256": sha256(source_path), "state_sha256": sha256(output),
                  "request_sha256": sha256(request_path), "ground_energy_certified": False}
        write_json(directory / "seed_measurement.json", record)
        records.append(record)
        print(json.dumps({"case_id": case, "initializer": sector, **checked}), flush=True)
    write_json(ROOT / "tranche_2/FIELD_INIT_ACCOUNTING.json", {
        "inprocess_cpu_seconds": time.process_time() - started,
        "wall_seconds": time.monotonic() - wall_started, "imports_excluded": True,
        "records": records})


if __name__ == "__main__":
    main()
