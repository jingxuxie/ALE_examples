import argparse
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import random
import secrets
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "authoring/vendor"))
import stim


def load_module(path, name):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def rank(values):
    basis = {}
    for value in values:
        while value:
            position = value.bit_length() - 1
            if position not in basis:
                basis[position] = value
                break
            value ^= basis[position]
    return len(basis)


def parity(values):
    result = 0
    for value in values:
        result ^= value
    return result


def store(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def heavy_word(columns, observable, bound):
    basis = {}
    supports = {}
    for index, column in enumerate(columns):
        value, support = column, 1 << index
        while value:
            leading = value.bit_length() - 1
            if leading not in basis:
                basis[leading], supports[leading] = value, support
                break
            value ^= basis[leading]
            support ^= supports[leading]
        if value == 0:
            selected = [location for location in range(512) if support >> location & 1]
            if len(selected) > bound and parity(observable[location] for location in selected):
                return {"faults": selected}
    raise RuntimeError("no heavy diagnostic logical word found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-before-tournament", action="store_true")
    parser.add_argument("--ratchet-case", type=Path)
    parser.add_argument("--bound", type=int, default=20)
    arguments = parser.parse_args()
    hidden = ROOT / "evaluator/hidden"
    hidden.mkdir(parents=True, exist_ok=True)
    if (hidden / "generation_manifest.json").exists():
        if arguments.ratchet_case:
            if not (ROOT / "adversary/generation_1/evaluator/hidden/reference_model.json").is_file():
                raise RuntimeError("ratchet requires an archived solved generation")
        elif not arguments.rebuild_before_tournament or list((ROOT / "adversary").glob("freeze_v_*.json")) or any((ROOT / "attempts").glob("v_*/*")):
            raise RuntimeError("refusing to overwrite a built or exposed instance")
        if arguments.rebuild_before_tournament:
            store(ROOT / "adversary/pre_freeze_audit.json", {
                "reason": "replace directly exposed MT19937 outputs with domain-separated HMAC-SHA256; avoid a generator-state shortcut",
                "previous_manifest": json.loads((hidden / "generation_manifest.json").read_text()),
                "tested_agents_had_access": False})
    secret_path = hidden / "generation_secret.json"
    seed_source = arguments.ratchet_case / "secret.json" if arguments.ratchet_case else secret_path
    seed = json.loads(seed_source.read_text())["seed"] if seed_source.exists() else secrets.randbits(256)
    bound = arguments.bound
    generator = random.Random(seed)
    key = seed.to_bytes(32, "big")

    def random_digest(namespace, index):
        return hmac.new(key, namespace + index.to_bytes(4, "big"), hashlib.sha256).digest()

    support = sorted(range(512), key=lambda index: random_digest(b"support", index))[:bound]
    columns = [int.from_bytes(random_digest(b"column", index)[:24], "big") for index in range(512)]
    columns[support[-1]] = parity(columns[index] for index in support[:-1])
    observable = [random_digest(b"observable", index)[0] & 1 for index in range(512)]
    if parity(observable[index] for index in support) == 0:
        observable[support[-1]] ^= 1
    if rank(columns) != 192 or len(set(columns)) != 512 or 0 in columns:
        raise RuntimeError("invalid generated check matrix")
    augmented = [column | (bit << 192) for column, bit in zip(columns, observable)]
    if rank(augmented) != 193:
        raise RuntimeError("observable not independent")
    column_set = set(columns)
    if any(columns[first] ^ columns[second] in column_set for first in range(512) for second in range(first)):
        raise RuntimeError("unexpected three-fault dependency")
    model = {"num_faults": 512, "num_detectors": 192, "num_observables": 1, "weight_bound": bound,
             "fault_probability": 0.001, "columns": [format(column, "048x") for column in columns],
             "observable": observable}
    store(ROOT / "participant/input/model.json", model)
    store(hidden / "reference_model.json", model)
    store(hidden / "witness/witness.json", {"faults": sorted(support)})
    store(hidden / "generation_secret.json", {"seed": seed, "support": sorted(support)})
    circuit = stim.Circuit()
    circuit.append("R", list(range(705)))
    circuit.append("X_ERROR", list(range(512)), 0.001)
    for detector in range(192):
        targets = [qubit for location, column in enumerate(columns) if column >> detector & 1 for qubit in (location, 512 + detector)]
        circuit.append("CX", targets)
        circuit.append("M", [512 + detector])
        circuit.append("DETECTOR", [stim.target_rec(-1)])
    circuit.append("CX", [qubit for location, bit in enumerate(observable) if bit for qubit in (location, 704)])
    circuit.append("M", [704])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
    (ROOT / "participant/input/memory.stim").write_text(str(circuit) + "\n")
    dem_lines = []
    for column, bit in zip(columns, observable):
        targets = ["D" + str(index) for index in range(192) if column >> index & 1]
        if bit:
            targets.append("L0")
        dem_lines.append("error(0.001) " + " ".join(targets))
    (ROOT / "participant/input/model.dem").write_text("\n".join(dem_lines) + "\n")
    compiled = circuit.detector_error_model().flattened()
    observed = set()
    for instruction in compiled:
        if instruction.type != "error":
            continue
        signature = 0
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                signature ^= 1 << target.val
            elif target.is_logical_observable_id():
                signature ^= 1 << 192
            else:
                raise RuntimeError("unexpected DEM separator")
        if abs(instruction.args_copy()[0] - 0.001) > 1e-14:
            raise RuntimeError("native fault probability changed")
        observed.add(signature)
    if observed != set(augmented) or len(observed) != 512:
        raise RuntimeError("native fault columns do not match")
    faulted = stim.Circuit()
    for operation in circuit:
        if operation.name == "X_ERROR":
            faulted.append("X", sorted(support))
        else:
            faulted.append(operation)
    samples = faulted.compile_sampler(seed=75612).sample(shots=8)
    if samples[:, :-1].any() or not samples[:, -1].all():
        raise RuntimeError("native planted witness not verified")
    clean = circuit.without_noise().compile_sampler(seed=11712).sample(shots=8)
    if clean.any():
        raise RuntimeError("nondeterministic or nonzero noiseless instrument")
    public_method = ROOT / "participant/input/overconfident_search.py"
    (hidden / "overconfident_search.py").write_bytes(public_method.read_bytes())
    method = load_module(public_method, "public_search")
    claim = method.search(model)
    if claim["faults"] or not claim["claimed_certified"]:
        raise RuntimeError("supplied search already found a valid witness")
    model_hash = hashlib.sha256((hidden / "reference_model.json").read_bytes()).hexdigest()
    claim["model_sha256"] = model_hash
    store(ROOT / "participant/input/claim.json", claim)
    baseline_answer = json.loads((arguments.ratchet_case / "champion_result.json").read_text())["answer"] if arguments.ratchet_case else {"faults": []}
    store(ROOT / "participant/baseline/witness.json", baseline_answer)
    store(ROOT / "adversary/baseline_claim.json", claim)
    store(hidden / "generation_manifest.json", {"model_sha256": model_hash, "stim_version": stim.__version__,
          "rank": 192, "augmented_rank": 193, "private_witness_weight": bound, "distinct_native_fault_signatures": 512,
          "no_zero_one_two_three_fault_syndromes": True, "generation_seed_private": True,
          "randomness": "domain-separated HMAC-SHA256 keyed by private 256-bit entropy"})
    public_hashes = {str(path.relative_to(ROOT)): {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                     for path in sorted((ROOT / "participant").rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    store(hidden / "public_hashes.json", public_hashes)
    evaluator = load_module(ROOT / "evaluator/evaluate.py", "private_checker")
    checker = load_module(ROOT / "participant/input/check_witness.py", "public_checker")
    witness = {"faults": sorted(support)}
    baseline_report = evaluator.evaluate_path(ROOT / "participant/baseline/witness.json")
    witness_report = evaluator.evaluate_path(hidden / "witness/witness.json")
    if not witness_report["passed"] or baseline_report["passed"]:
        raise RuntimeError("end-to-end certificate checks failed")
    comparisons = 0
    for trial in range(200):
        artifact = {"faults": generator.sample(range(512), generator.randrange(bound + 11))}
        public = checker.check(model, artifact)
        private = evaluator.evaluate_data(model, artifact)
        if public != private:
            raise RuntimeError("independent row and column checkers disagree")
        comparisons += 1
    heavy = heavy_word(columns, observable, bound)
    store(ROOT / "adversary/heavy_invalid/witness.json", heavy)
    heavy_report = evaluator.evaluate_path(ROOT / "adversary/heavy_invalid/witness.json")
    if heavy_report["valid"] or heavy_report["detector_weight"] or heavy_report["logical_parity"] != 1:
        raise RuntimeError("weight-bound checker failure")
    mutants = [{"faults": [support[0], support[0]]}, {"faults": [True]}, {"faults": [512]},
               {"faults": [-1]}, {"faults": [0.0]}, {"faults": [], "score": 1}, {"faults": "bad"}]
    rejected = 0
    for artifact in mutants:
        try:
            evaluator.evaluate_data(model, artifact)
        except ValueError:
            rejected += 1
    if rejected != len(mutants):
        raise RuntimeError("malformed witness accepted")
    report = {"passed": True, "native_fault_signatures": 512, "native_witness_shots": 8,
              "native_noiseless_shots": 8, "independent_checker_comparisons": comparisons,
              "malformed_rejections": rejected, "heavy_exact_logical_rejected": heavy_report,
              "baseline": baseline_report, "private_witness": witness_report}
    store(ROOT / "adversary/validation.json", report)
    store(ROOT / "status.json", {"concept": "bounded_distance_certificate_falsification", "verification_mode": "B",
              "phase": "validated_awaiting_fresh_tournament", "final_status": None,
              "baseline": baseline_report, "private_witness": witness_report, "known_passing_solution": True,
              "fresh_attempts": [], "ratchet_generations": int(bool(arguments.ratchet_case))})
    for directory in ("attempts/v_1", "attempts/v_2", "champions"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
