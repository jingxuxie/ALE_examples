import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / "participant"))
from reference_core import input_witness
from reference_faults import compiled_schedule, fault_weights, omission_profile

for name in sys.argv[1:]:
    circuit = json.loads((ROOT / name).read_text())
    qubits = len(circuit["layers"][0]["local"])
    profile = omission_profile(qubits, circuit["layers"], collect=True)
    schedule, instances = compiled_schedule(circuit["layers"])
    print(name, "minimum", profile["minimum"], "failures", profile["failed_scenario_counts"], flush=True)
    for record in profile["scenario_records"]:
        if min(record["minima"]) >= 3:
            continue
        omitted = record["omitted_instances"]
        weights = fault_weights(qubits, schedule, omitted)
        for stratum, values in zip(("single", "double"), weights[0]):
            for index in (values < 3).nonzero()[0]:
                print("  omitted", [instances[instance] for instance in omitted], "input",
                      input_witness(qubits, stratum, int(index)), "weight", int(values[index]), flush=True)
