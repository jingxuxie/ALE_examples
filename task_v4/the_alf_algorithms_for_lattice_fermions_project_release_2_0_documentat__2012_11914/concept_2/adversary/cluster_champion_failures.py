import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "adversary/champion_audit_clusters_v1"
specification = importlib.util.spec_from_file_location("stable_audit", ROOT / "adversary/champion_audit.py")
audit = importlib.util.module_from_spec(specification)
specification.loader.exec_module(audit)


def save_regime(name, instances, records, law):
    summary = audit.summarize(records)
    summary["law"] = law
    summary["by_step_and_observable"] = {f"h={step}:{observable}": audit.summarize([record for record in records if record["dtau"] == step and record["observable"] == observable]) for step in sorted({record["dtau"] for record in records}) for observable in ("propagator", "green")}
    audit.write_json(DIRECTORY / (name + "_summary.json"), summary)
    worst = []
    identifiers = set()
    for record in sorted(records, key=lambda record: record["ratio"], reverse=True):
        if record["case_id"] not in identifiers:
            worst.append(record)
            identifiers.add(record["case_id"])
        if len(worst) == 12:
            break
    audit.write_json(DIRECTORY / (name + "_worst_fixtures.json"), {"instances": [instance for instance in instances if instance["id"] in identifiers], "worst_records": worst})
    with (DIRECTORY / (name + "_points.jsonl")).open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(json.dumps({"regime": name, "cases": summary["cases"], "points": summary["points"], "max_ratio": summary["max_point_ratio"], "failed_cases": summary["cases_above_original_cap"], "worst": summary["worst"]}), flush=True)
    return summary


def main():
    started = time.monotonic()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    source = ROOT / "adversary/champion_audit_v1"
    candidate_bytes = (source / "candidate.json").read_bytes()
    candidate = json.loads(candidate_bytes)["stages"]
    baseline = json.loads((source / "baseline.json").read_text())["stages"]
    rules = json.loads((source / "original_contract.json").read_text())
    generator = audit.load_module("cluster_generator", ROOT / "evaluator/hidden/generate.py")
    for name in ("candidate.json", "baseline.json", "original_contract.json"):
        (DIRECTORY / name).write_bytes((source / name).read_bytes())
    summaries = {}

    def scan(instances, steps):
        records = []
        for offset in range(0, len(instances), 48):
            records.extend(audit.audit_batch(instances[offset:offset + 48], candidate, baseline, rules["components"], steps))
        return records

    flux_rules = copy.deepcopy(rules)
    flux_rules["sampling"]["families"] = [family for family in rules["sampling"]["families"] if family["name"] == "flux_disordered"]
    instances = generator.draw_suite(flux_rules, 82843100, 1536)["instances"]
    records = scan(instances, [0.4, 0.6, 0.8, 1.0])
    summaries["focused_flux"] = save_regime("focused_flux", instances, records, {"couplings": "exact original flux_disordered family law, independent fresh draws", "shapes": [[4,4],[4,6],[6,4]], "seed": 82843100, "count":1536,"only_extension":"h includes .6,.8,1.0"})

    flux_rules["sampling"]["lattice_shapes"] = [[6,6],[6,8],[8,8]]
    instances = generator.draw_suite(flux_rules, 82843101, 384)["instances"]
    records = scan(instances, [0.4, 0.6, 0.8, 1.0])
    summaries["focused_flux_large"] = save_regime("focused_flux_large", instances, records, {"couplings": "exact original flux_disordered family law, independent fresh draws", "shapes": [[6,6],[6,8],[8,8]], "seed":82843101,"count":384,"extensions":"larger tori and h includes .6,.8,1.0"})

    witnesses = json.loads((source / "larger_steps_worst_fixtures.json").read_text())
    anchors = [next(instance for instance in witnesses["instances"] if instance["id"] == record["case_id"]) for record in witnesses["worst_records"][:2]]
    variants = []
    random = np.random.default_rng(82843200)
    for anchor_index, anchor in enumerate(anchors):
        for sample in range(192):
            instance = copy.deepcopy(anchor)
            instance["id"] = f"local_{anchor_index}_{sample}"
            for bond in instance["bonds"]:
                bond[3] *= float(random.uniform(0.97,1.03))
                bond[4] += float(random.uniform(-0.02,0.02))
            instance["site_potential"] = (np.array(instance["site_potential"]) + random.uniform(-0.03,0.03,len(instance["site_potential"]))).tolist()
            instance["anchor"] = anchor["id"]
            variants.append(instance)
    records = scan(variants, [0.4,0.6,0.8,1.0])
    summaries["local_robustness"] = save_regime("local_robustness", variants, records, {"purpose":"local robustness only, not a proposed hidden law or an iid original-law claim", "anchors":[anchor["id"] for anchor in anchors],"count_per_anchor":192,"seed":82843200,"perturbations":"each bond amplitude times U[.97,1.03]; each phase plus U[-.02,.02]; each site potential plus U[-.03,.03], independently"})

    ablations = []
    for anchor in anchors:
        for treatment in ("unchanged", "zero_phases", "half_fields", "half_hopping"):
            instance = copy.deepcopy(anchor)
            instance["id"] = anchor["id"] + ":" + treatment
            if treatment == "zero_phases":
                for bond in instance["bonds"]:
                    bond[4] = 0.0
            if treatment == "half_hopping":
                for bond in instance["bonds"]:
                    bond[3] *= 0.5
            if treatment == "half_fields":
                instance["site_potential"] = (np.array(instance["site_potential"]) * 0.5).tolist()
            ablations.append(instance)
    records = scan(ablations, [0.08,0.16,0.28,0.4,0.6,0.8,1.0])
    audit.write_json(DIRECTORY / "ablation_records.json", {"instances": ablations,"records":records})

    commutators = []
    uniform_instances = []
    for shape_index, shape in enumerate([[4,4],[4,6],[6,4],[6,6],[6,8],[8,8]]):
        uniform_rules = copy.deepcopy(rules)
        uniform_rules["sampling"]["lattice_shapes"] = [shape,shape,shape]
        cases = generator.draw_suite(uniform_rules, 82843300 + shape_index, 24)["instances"]
        for instance in cases:
            instance["id"] = str(shape) + ":" + instance["id"]
            for bond in instance["bonds"]:
                bond[3] = 1.0
                bond[4] = 0.0
            uniform_instances.append(instance)
        dimension = math.prod(shape)
        matrices = {label: np.zeros((dimension,dimension)) for label in rules["components"]}
        for label, first, second, amplitude, phase in cases[0]["bonds"]:
            matrices[label][first,second] = matrices[label][second,first] = -1.0
        commutators.append({"shape":shape,"X_commutator_F_over_sqrt_N":float(np.linalg.norm(matrices["X0"] @ matrices["X1"] - matrices["X1"] @ matrices["X0"]) / np.sqrt(dimension)),"Y_commutator_F_over_sqrt_N":float(np.linalg.norm(matrices["Y0"] @ matrices["Y1"] - matrices["Y1"] @ matrices["Y0"]) / np.sqrt(dimension))})
    records = scan(uniform_instances, [0.4])
    summaries["uniform_hopping_geometry"] = save_regime("uniform_hopping_geometry", uniform_instances, records, {"law":"t=1 uniform real hopping, no dimerization/disorder/flux; onsite fields independently follow all four original family onsite laws; 24 cases per family per shape", "seed_base":82843300,"purpose":"controlled algebra diagnostic, not the original hopping law"})
    audit.write_json(DIRECTORY / "commutator_geometry.json", {"commutators":commutators,"by_shape":{str(shape):audit.summarize([record for record in records if record["case_id"].startswith(str(shape)+':')]) for shape in [[4,4],[4,6],[6,4],[6,6],[6,8],[8,8]]}})
    audit.write_json(DIRECTORY / "summary.json", {"candidate_sha256":hashlib.sha256(candidate_bytes).hexdigest(),"elapsed_wall_seconds":time.monotonic()-started,"regimes":summaries,"participant_or_targets_modified":False})
    print("CLUSTER_AUDIT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
