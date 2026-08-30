import collections
import hashlib
import itertools
import json
import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from core import input_witness, load_json, validate_submission
from faults import compiled_schedule, fault_weights, omission_profile


def sweep_family(family, circuit):
    schedule, instances = compiled_schedule(circuit["layers"])
    proper_minima = {}
    round_triples = collections.Counter()
    implicated = collections.Counter()
    round_spans = collections.Counter()
    distinct_qubits = collections.Counter()
    failed_weight_counts = collections.Counter()
    selected = {1: [], 2: []}
    third_order = 0
    scenario_count = 0
    started = time.perf_counter()

    def consume(omitted, minima):
        nonlocal third_order, scenario_count
        scenario_count += 1
        if len(omitted) <= 2:
            proper_minima[omitted] = min(minima)
        elif min(minima) < 3:
            weight = min(minima)
            failed_weight_counts[weight] += 1
            gates = [instances[index] for index in omitted]
            rounds = tuple(gate["round"] for gate in gates)
            round_triples[str(rounds)] += 1
            round_spans[str(max(rounds) - min(rounds))] += 1
            distinct_qubits[str(len({qubit for gate in gates for qubit in (gate["control"], gate["target"])}))] += 1
            implicated.update(omitted)
            if all(proper_minima[subset] >= 3 for count in (1, 2) for subset in itertools.combinations(omitted, count)):
                third_order += 1
            if weight in selected and len(selected[weight]) < 12:
                selected[weight].append(omitted)
        if scenario_count % 20000 == 0:
            print(family["id"], scenario_count, "seconds", round(time.perf_counter() - started, 2), flush=True)

    profile = omission_profile(family["n"], circuit["layers"], maximum=3, on_scenario=consume)
    witnesses = []
    names = ("forward.single", "forward.double", "inverse.single", "inverse.double")
    for omitted in selected[1] + selected[2]:
        flattened = [values for strata in fault_weights(family["n"], schedule, omitted) for values in strata]
        minima = [int(values.min()) for values in flattened]
        stratum_index = minima.index(min(minima))
        direction, stratum = names[stratum_index].split(".")
        witnesses.append({"omissions": [instances[index] for index in omitted],
                          "direction": direction, "stratum": stratum,
                          "input": input_witness(family["n"], stratum, int(flattened[stratum_index].argmin())),
                          "output_weight": minima[stratum_index]})
    profile["clusters"] = {"genuinely_third_order_failures": third_order,
                           "failed_weight_counts": dict(failed_weight_counts),
                           "by_round_triple": dict(round_triples), "by_round_span": dict(round_spans),
                           "distinct_endpoint_qubits": dict(distinct_qubits),
                           "most_implicated_instances": [{"instance": instances[index], "failed_triples": count}
                                                         for index, count in implicated.most_common(16)]}
    profile["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    profile["witnesses"] = witnesses
    (WORK / (family["id"] + "_triple_sweep.json")).write_text(json.dumps(profile, indent=2) + "\n")
    print("FINISHED", family["id"], profile["minimum"], profile["by_omission_count"]["3"]["failed_scenarios"],
          profile["runtime_seconds"], profile["peak_rss_bytes"], flush=True)
    return profile


def main():
    spec, spec_hash = load_json(ROOT / "evaluator/hidden/frozen_spec.json")
    artifact, artifact_hash = load_json(ROOT / "champions/generation_2/artifact.json")
    circuits = validate_submission(artifact, spec)
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(sweep_family, family, circuits[family["id"]]) for family in spec["families"]]
        profiles = [future.result() for future in futures]
    report = {"source": "champions/generation_2/artifact.json", "source_sha256": artifact_hash,
              "spec_sha256_at_sweep": spec_hash, "maximum_omissions": 3,
              "minimum_required": 3, "runtime_seconds": time.perf_counter() - started,
              "workers": 3, "families": {family["id"]: profile for family, profile in zip(spec["families"], profiles)}}
    (WORK / "champion_triple_sweep.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
