import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


def main():
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    payload = json.loads(raw)
    original = verify.verify(payload)
    gates = verify.make_gates(payload)
    baseline_gates = verify.make_gates(verify.uniform_payload())
    family_records = []
    for name, selection in (("single", range(24)), ("cx", range(24, 32))):
        observed = {pauli: sum(gates[index]["counts"].get(pauli, 0) for index in selection)
                    for pauli in verify.PAULIS[1:]}
        expected = {pauli: sum(baseline_gates[index]["counts"].get(pauli, 0) for index in selection)
                    for pauli in verify.PAULIS[1:]}
        defects = [{"pauli": "".join("IXZY"[digit] for digit in pauli), "actual": observed[pauli],
                    "expected": expected[pauli], "difference": observed[pauli] - expected[pauli]}
                   for pauli in observed if observed[pauli] != expected[pauli]]
        overlap = sum(sum(count * gates[index]["counts"].get(verify.transform(gates[index]["key"], pauli), 0)
                          for pauli, count in gates[gates[index]["inverse"]]["counts"].items())
                      for index in selection)
        family_records.append({"family": name, "mean_channel_defects": defects,
                               "max_mean_count_defect": max(abs(row["difference"]) for row in defects),
                               "overlap": overlap, "overlap_target": 28800 if name == "single" else 1920})
    sweep = []
    for eta in (0.35, 0.4, 0.45):
        eta_fraction = Fraction(str(eta))
        for gate in gates:
            gate["weight"] = float(40 * ((1 - eta_fraction) / 24 if gate["key"][0] == "single" else eta_fraction / 8))
        for gate in baseline_gates:
            gate["weight"] = float(40 * ((1 - eta_fraction) / 24 if gate["key"][0] == "single" else eta_fraction / 8))
        values, _, transfer_evidence = verify.transfers(gates)
        baseline_values, _, _ = verify.transfers(baseline_gates)
        fitted = verify.fit(values)
        overlap_difference = ((1 - eta_fraction) * Fraction(25466 - 28800, 24 * 3600)
                              + eta_fraction * Fraction(3587 - 1920, 8 * 3600))
        exact_S2_difference = Fraction(256, 255) * Fraction(1, 50) ** 2 * overlap_difference
        observed_difference = float(values[1] - baseline_values[1])
        if abs(observed_difference - float(exact_S2_difference)) > 1e-13:
            raise AssertionError("Independent exact sampler-calibration proof failed")
        sweep.append({"eta": eta, "fit": fitted, "S256": float(values[-1]),
                      "S2_difference": observed_difference, "S2_difference_exact": str(exact_S2_difference),
                      "transfer": transfer_evidence,
                      "original_numeric_gates_pass": bool(fitted["bias"] >= 0.0244 and fitted["max_residual"] <= 0.004 and values[-1] >= 0.005)})
    print(json.dumps({"champion_sha256": hashlib.sha256(raw).hexdigest(),
                      "original_contract_pass": original["accepted"], "original_fit": original["fit"],
                      "family_checks": family_records, "sampler_sweep": sweep,
                      "generation2_family_calibrations_pass": False}, indent=2))


if __name__ == "__main__":
    main()
