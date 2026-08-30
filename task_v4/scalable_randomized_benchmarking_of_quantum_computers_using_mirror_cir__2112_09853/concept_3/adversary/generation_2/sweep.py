import collections
import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from core import load_json, validate_submission
from faults import omission_profile


def main():
    spec, spec_hash = load_json(ROOT / "evaluator/hidden/frozen_spec.json")
    artifact, artifact_hash = load_json(ROOT / "champions/generation_1/artifact.json")
    circuits = validate_submission(artifact, spec)
    result = {"source": "champions/generation_1/artifact.json", "artifact_sha256": artifact_hash,
              "spec_sha256_at_sweep": spec_hash, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "minimum_required": 3, "max_omissions": 2, "families": {}}
    for family in spec["families"]:
        profile = omission_profile(family["n"], circuits[family["id"]]["layers"], collect=True)
        records = profile.pop("scenario_records")
        instances = profile["instances"]
        (WORK / (family["id"] + "_fault_records.json")).write_text(json.dumps(records, separators=(",", ":")) + "\n")
        singles = {record["omitted_instances"][0]: min(record["minima"]) for record in records if len(record["omitted_instances"]) == 1}
        round_pairs = collections.Counter()
        shared_endpoint = collections.Counter()
        implicated = collections.Counter()
        synergy = 0
        inherited = 0
        for record in records:
            omitted = record["omitted_instances"]
            if len(omitted) != 2 or min(record["minima"]) >= 3:
                continue
            first, second = omitted
            first_gate, second_gate = instances[first], instances[second]
            rounds = tuple(sorted((first_gate["round"], second_gate["round"])))
            round_pairs[str(rounds)] += 1
            shared = bool({first_gate["control"], first_gate["target"]}.intersection((second_gate["control"], second_gate["target"])))
            shared_endpoint[str(shared)] += 1
            implicated.update(omitted)
            if singles[first] >= 3 and singles[second] >= 3:
                synergy += 1
            else:
                inherited += 1
        profile["clusters"] = {"synergistic_double_failures": synergy,
                               "double_failures_with_a_failing_single": inherited,
                               "by_round_pair": dict(round_pairs), "shared_endpoint": dict(shared_endpoint),
                               "most_implicated_instances": [{"instance": instances[index], "failed_pairs": count}
                                                             for index, count in implicated.most_common(12)]}
        result["families"][family["id"]] = profile
        print(family["id"], profile["by_omission_count"], profile["clusters"], "seconds", profile["runtime_seconds"], flush=True)
    (WORK / "champion_omission_sweep.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
