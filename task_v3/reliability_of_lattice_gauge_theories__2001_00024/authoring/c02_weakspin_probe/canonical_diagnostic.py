import argparse
import hashlib
import json
import math
import os
import resource
import signal
import time

from probe import LEVELS, ROOT, SIDE, load, save, sha

import charge_engine
from engine import np
from evaluator import score_result


IDENTIFIER = "weak_spin1_V0p5_L32_T8"
DESTINATION = "diagnostics/canonical_coarse_T8"


def fingerprint(state):
    digest = hashlib.sha256()
    digest.update(repr((state.form, state.norm, state.chi)).encode())
    for tensor in state._B:
        digest.update(tensor.to_ndarray().tobytes())
    for singular_values in state._S:
        digest.update(np.asarray(singular_values).tobytes())
    return digest.hexdigest()


def measure(state, pairs):
    density = np.real(state.expectation_value("number"))
    flux_square = np.real(state.expectation_value("flux_sq"))
    right_square = np.real(state.expectation_value("flux_number_sq"))
    violation = [float(np.real(state.expectation_value("gauss0_sq", sites=[0])[0]))]
    for site in range(1, state.L):
        cross = state.expectation_value_term([("flux", site - 1), ("flux_number", site)])
        violation.append(float(flux_square[site - 1] + right_square[site] + 2 * np.real(cross)))
    correlations = []
    for left, right in pairs:
        joint = state.expectation_value_term([("number", left), ("number", right)])
        correlations.append(float(np.real(joint) - density[left] * density[right]))
    return {"density": density.tolist(), "violation": violation, "correlation": correlations}


def run(cpu, timeout):
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    signal.alarm(timeout)
    start = time.monotonic()
    manifest, entry, case = load(IDENTIFIER)
    for relative, expected in manifest["source_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError("frozen source changed: " + relative)
    original_engine_class = charge_engine.TEBDEngine
    measurements = []
    signs = (-1.0) ** np.arange(case["experiment"]["length"])

    def record(state):
        measurement_start = time.monotonic()
        index = len(measurements)
        original_hash = fingerprint(state)
        norm_before = state.norm_test()
        direct = measure(state, case["pairs"])
        copied_state = state.copy()
        copied_state.canonical_form(cutoff=0)
        norm_after = copied_state.norm_test()
        canonical = measure(copied_state, case["pairs"])
        after_hash = fingerprint(state)
        if original_hash != after_hash:
            raise RuntimeError("diagnostic modified the evolving state")
        result = {"time": case["times"][index], "direct": direct, "canonical_copy": canonical,
                  "norm_test_before": norm_before.tolist(), "norm_test_after": norm_after.tolist(),
                  "norm_test_max_before": float(np.max(norm_before)),
                  "norm_test_max_after": float(np.max(norm_after)),
                  "norm_test_frobenius_before": float(np.linalg.norm(norm_before)),
                  "norm_test_frobenius_after": float(np.linalg.norm(norm_after)),
                  "sum_Q_before": float(np.asarray(direct["density"]) @ signs),
                  "sum_Q_after": float(np.asarray(canonical["density"]) @ signs),
                  "sector_before": state.get_total_charge(only_physical_legs=True).tolist(),
                  "sector_after": copied_state.get_total_charge(only_physical_legs=True).tolist(),
                  "bond_sizes_before": state.chi, "bond_sizes_after": copied_state.chi,
                  "evolving_state_sha256_before": original_hash,
                  "evolving_state_sha256_after": after_hash, "evolving_state_unchanged": True,
                  "measurement_seconds": time.monotonic() - measurement_start}
        measurements.append(result)
        save(DESTINATION + "/measurement_" + str(index).zfill(2) + ".json", result)
        print(json.dumps({name: result[name] for name in ("time", "norm_test_max_before", "norm_test_max_after",
                                                        "sum_Q_before", "sum_Q_after", "measurement_seconds")}), flush=True)

    class DiagnosticTEBD(original_engine_class):
        def __init__(self, *arguments, **keywords):
            super().__init__(*arguments, **keywords)
            record(self.psi)

        def run_evolution(self, steps, timestep):
            result = super().run_evolution(steps, timestep)
            record(self.psi)
            return result

    try:
        charge_engine.TEBDEngine = DiagnosticTEBD
        prediction, audit = charge_engine.predict(case["experiment"], entry["true_parameters"],
                                                 case["times"], case["pairs"], **LEVELS["coarse"])
    finally:
        charge_engine.TEBDEngine = original_engine_class
    canonical_prediction = {"parameters": entry["true_parameters"]}
    for name in ("density", "violation", "correlation"):
        canonical_prediction[name] = [measurement["canonical_copy"][name] for measurement in measurements]
    coarse_path = SIDE / "references" / IDENTIFIER / "coarse.json"
    coarse = json.loads(coarse_path.read_text())
    reproduction = {name: float(np.max(np.abs(np.asarray(prediction[name]) - np.asarray(coarse["prediction"][name]))))
                    for name in ("density", "violation", "correlation")}
    shifts = {name: float(np.max(np.abs(np.asarray(canonical_prediction[name]) - np.asarray(prediction[name]))))
              for name in ("density", "violation", "correlation")}
    components, errors = score_result(canonical_prediction, prediction)
    result = {"case": IDENTIFIER, "case_file_sha256": entry["case_file_sha256"],
              "diagnostic_script_sha256": sha(__file__), "coarse_reference_sha256": sha(coarse_path),
              "method": "Process-local TEBD subclass observes the original evolving state and canonicalizes only a deep-value MPS copy at each requested output time; cutoff=0.",
              "original_sources_unchanged": all(sha(ROOT / relative) == expected for relative, expected in manifest["source_sha256"].items()),
              "prediction_direct": prediction, "prediction_canonical_copy": canonical_prediction,
              "measurements": measurements, "audit": audit,
              "original_coarse_reproduction_maximum_differences": reproduction,
              "canonical_readout_maximum_changes": shifts,
              "measurement_change_components": components, "measurement_change_errors": errors,
              "measurement_change_geometric_core": math.prod(components.values()) ** 0.25,
              "all_evolving_states_unchanged": all(measurement["evolving_state_unchanged"] for measurement in measurements),
              "all_measurements_complete": len(measurements) == len(case["times"]),
              "seconds": time.monotonic() - start,
              "cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
              "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "timeout_seconds": timeout,
              "interpretation": "Measurement-assumption diagnostic only. No new accepted label, no participant score, no change to the truncating dynamics or frozen engine."}
    save(DESTINATION + "/result.json", result)
    signal.alarm(0)
    print(json.dumps({name: result[name] for name in ("seconds", "cpu_seconds", "max_rss_kib",
                                                     "original_coarse_reproduction_maximum_differences",
                                                     "canonical_readout_maximum_changes",
                                                     "all_evolving_states_unchanged", "original_sources_unchanged")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--timeout", type=int, default=900)
    arguments = parser.parse_args()
    run(arguments.cpu, arguments.timeout)
