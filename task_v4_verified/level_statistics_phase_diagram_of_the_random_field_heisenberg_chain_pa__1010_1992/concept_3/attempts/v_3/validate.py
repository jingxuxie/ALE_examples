import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import resource
import secrets
import time
import numpy as np
from search import ASSETS, OUTPUT, bank
from exact import assess, hamiltonian, proxy_statistics, spectrum, validate_witness


def check(task):
    witness, protocol, label = task
    started = time.monotonic()
    report = assess(witness, protocol)
    report["validation_label"] = label
    report["seconds"] = time.monotonic() - started
    report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return report


def summary(report):
    return {"label": report["validation_label"], "pass": report["pass"], "valid": report["valid"],
            "core": report["core"], "worst_family": report["worst_family"],
            "base": report["base"]["signed_difference"], "seconds": report["seconds"],
            "family_means": [family["mean"] for family in report["families"]],
            "coverage": [family["above_member_floor"] for family in report["families"]],
            "minimum_gap": min([report["base"]["minimum_gap"]] + [member["minimum_gap"] for member in report["members"]]),
            "minimum_symmetry_distance": min([report["constraints"]["symmetry_distance"]] + [member["constraints"]["symmetry_distance"] for member in report["members"]])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness", type=Path, default=OUTPUT / "witness.json")
    parser.add_argument("--banks", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tag", default="final-validation")
    args = parser.parse_args()
    witness_bytes = args.witness.read_bytes()
    witness = json.loads(witness_bytes)
    assert args.witness.is_file() and not args.witness.is_symlink()
    assert len(witness_bytes) <= 16384
    validate_witness(witness)
    public_bytes = (ASSETS / "input/protocol.json").read_bytes()
    commitment = json.loads((ASSETS / "input/commitment.json").read_text())
    assert hashlib.sha256(public_bytes).hexdigest() == commitment["public_protocol_sha256"]
    public = json.loads(public_bytes)
    seed_hex = public["generator"]["seed_hex"]
    for family in public["families"]:
        for member, offset in enumerate(family["offsets"]):
            uniforms = np.array([2.0 * int.from_bytes(hashlib.sha256(f"{seed_hex}|{family['name']}|{member}|{site}".encode()).digest()[:8], "big") / (2**64 - 1) - 1.0 for site in range(12)])
            regenerated = family["amplitude_before_centering"] * (uniforms - uniforms.mean())
            assert np.array_equal(regenerated, offset)
    energies = spectrum(witness["fields"])
    alternate = spectrum(witness["fields"], driver="evd")
    maximum_error = float(np.max(np.abs(energies - alternate)))
    assert maximum_error < 1e-10
    assert abs(proxy_statistics(energies)["difference"] - proxy_statistics(alternate)["difference"]) < 1e-8
    matrix = hamiltonian(witness["fields"])
    assert np.array_equal(matrix, matrix.T)
    assert abs(energies.sum() - np.trace(matrix)) < 1e-9
    assert abs(np.dot(energies, energies) - np.sum(matrix * matrix)) < 1e-7
    reports_dir = OUTPUT / args.tag
    reports_dir.mkdir(exist_ok=True)
    public_report = check((witness, public, "public_calibration"))
    (reports_dir / "public.json").write_text(json.dumps(public_report, indent=2) + "\n")
    print(json.dumps(summary(public_report)), flush=True)
    tasks = []
    for index in range(args.banks):
        label = f"{args.tag}-{index}"
        protocol = bank(label, seed_hex=secrets.token_hex(32))
        (reports_dir / f"protocol-{index}.json").write_text(json.dumps(protocol, indent=2) + "\n")
        tasks.append((witness, protocol, label))
    summaries = [summary(public_report)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        for index, report in enumerate(executor.map(check, tasks)):
            (reports_dir / f"replication-{index}.json").write_text(json.dumps(report, indent=2) + "\n")
            summaries.append(summary(report))
            print(json.dumps(summaries[-1]), flush=True)
    result = {"witness_sha256": hashlib.sha256(witness_bytes).hexdigest(),
              "independent_bank_count": args.banks, "private_bank_tested": False,
              "public_generator_reproduced_exactly": True,
              "base_evr_evd_maximum_error": maximum_error,
              "all_validation_banks_pass": all(row["pass"] for row in summaries),
              "reports": summaries}
    (reports_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    if not result["all_validation_banks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
