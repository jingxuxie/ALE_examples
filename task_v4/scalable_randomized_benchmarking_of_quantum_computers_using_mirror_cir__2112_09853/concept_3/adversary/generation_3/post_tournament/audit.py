import concurrent.futures
import hashlib
import itertools
import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from core import circuit_weights, load_json, score_metrics, summarize, validate_submission

WORDS = ("I", "H", "S", "HS", "SH", "HSH")
ATTEMPTS = ("v_3", "v_4")
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "REPORT": "1"}
for variable in ("CEX", "EXACT", "VERIFY", "FIXED"):
    ENV.pop(variable, None)


def digest(path):
    checksum = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("not a regular file")
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            checksum.update(block)
    return checksum.hexdigest()


def write(name, value):
    (WORK / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def inventory(directory):
    regular = {}
    nonregular = []
    for current, directories, filenames in os.walk(directory, followlinks=False):
        for name in list(directories):
            path = Path(current) / name
            if path.is_symlink():
                directories.remove(name)
                nonregular.append(str(path.relative_to(directory)))
        for name in filenames:
            path = Path(current) / name
            relative = str(path.relative_to(directory))
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                nonregular.append(relative)
                continue
            regular[relative] = digest(path)
    return regular, nonregular


def fingerprint_audit():
    result = {}
    for attempt in ATTEMPTS:
        metadata = json.loads((ROOT / "attempts" / (attempt + "_audit") / "metadata.json").read_text())
        expected = metadata["submission_sha256"]
        observed, nonregular = inventory(ROOT / "attempts" / attempt)
        changed = sorted(path for path in expected.keys() & observed.keys() if expected[path] != observed[path])
        result[attempt] = {"deadline_expected_files": len(expected), "current_regular_files": len(observed),
                           "changed": changed, "missing": sorted(expected.keys() - observed.keys()),
                           "extra": sorted(observed.keys() - expected.keys()), "nonregular": nonregular,
                           "unchanged": observed == expected and not nonregular,
                           "deadline_sha256": expected, "current_sha256": observed,
                           "metadata_sha256": digest(ROOT / "attempts" / (attempt + "_audit") / "metadata.json"),
                           "helper_participant_unchanged": metadata["participant_unchanged"],
                           "participant_current_matches_launch": all(digest(ROOT / "participant" / path) == checksum
                                                                      for path, checksum in metadata["participant_before"].items())}
    return result


def scalar(nqubits, layers, input_pauli, omissions, inverse=False):
    xbits = [0] * nqubits
    zbits = [0] * nqubits
    for entry in input_pauli:
        xbits[entry["qubit"]] = int(entry["pauli"] in ("X", "Y"))
        zbits[entry["qubit"]] = int(entry["pauli"] in ("Z", "Y"))
    deleted = {(entry["round"], entry["cx_index"]) for entry in omissions}
    for entry in omissions:
        assert layers[entry["round"]]["cx"][entry["cx_index"]] == [entry["control"], entry["target"]]
    rounds = reversed(range(len(layers))) if inverse else range(len(layers))
    for round_index in rounds:
        layer = layers[round_index]
        gates = list(enumerate(layer["cx"]))
        if inverse:
            for gate_index, (control, target) in reversed(gates):
                if (round_index, gate_index) not in deleted:
                    xbits[target] ^= xbits[control]
                    zbits[control] ^= zbits[target]
        for qubit, word in enumerate(layer["local"]):
            for gate in reversed(word) if inverse else word:
                if gate == "H":
                    xbits[qubit], zbits[qubit] = zbits[qubit], xbits[qubit]
                elif gate == "S":
                    zbits[qubit] ^= xbits[qubit]
        if not inverse:
            for gate_index, (control, target) in gates:
                if (round_index, gate_index) not in deleted:
                    xbits[target] ^= xbits[control]
                    zbits[control] ^= zbits[target]
    return [{"qubit": qubit, "pauli": "Y" if xbits[qubit] and zbits[qubit] else "X" if xbits[qubit] else "Z"}
            for qubit in range(nqubits) if xbits[qubit] or zbits[qubit]]


def parse_text_circuit(path, families):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 2_000_000:
        return None
    text = path.read_text()
    if re.fullmatch(r"[\s0-9+-]+", text) is None:
        return None
    values = iter(map(int, text.split()))
    width, depth = next(values), next(values)
    family = next((entry for entry in families if entry["n"] == width), None)
    if family is None or not 0 <= depth <= family["max_rounds"]:
        return None
    layers = []
    for _ in range(depth):
        local = []
        for _ in range(width):
            index = next(values)
            if not 0 <= index < len(WORDS):
                raise ValueError("invalid local-word index")
            local.append(WORDS[index])
        count = next(values)
        if not 0 <= count <= width // 2:
            raise ValueError("invalid matching length")
        layers.append({"local": local, "cx": [[next(values), next(values)] for _ in range(count)]})
    if next(values, None) is not None:
        raise ValueError("trailing tokens")
    return {"family": family["id"], "layers": layers}


def main():
    started = time.monotonic()
    spec, spec_hash = load_json(ROOT / "evaluator/hidden/frozen_spec.json")
    families = {family["id"]: family for family in spec["families"]}
    before = fingerprint_audit()
    write("fingerprints_before.json", before)
    empty = {"schema_version": 1, "circuits": [{"family": name, "layers": []} for name in families]}
    candidates = {}
    rejected = []
    full_artifacts = []
    inspected = []

    def add(circuit, source, encoding, attempt=None, pointer=""):
        wrapped = {"schema_version": 1, "circuits": [circuit if name == circuit.get("family") else {"family": name, "layers": []} for name in families]}
        if circuit.get("family") not in families:
            raise ValueError("unknown hardware family")
        validate_submission(wrapped, spec)
        canonical = json.dumps(circuit, sort_keys=True, separators=(",", ":"))
        identity = hashlib.sha256(canonical.encode()).hexdigest()
        record = {"path": str(source.relative_to(ROOT)), "encoding": encoding, "attempt": attempt, "json_pointer": pointer,
                  "deadline_eligible": attempt is None or before[attempt]["current_sha256"].get(str(source.relative_to(ROOT / "attempts" / attempt))) == before[attempt]["deadline_sha256"].get(str(source.relative_to(ROOT / "attempts" / attempt)))}
        if identity not in candidates:
            family = families[circuit["family"]]
            metrics = summarize(family["n"], circuit_weights(family["n"], circuit["layers"]))
            ideal_score, failures = score_metrics(metrics, family["targets"])
            candidates[identity] = {"family": circuit["family"], "circuit": circuit, "sources": [], "ideal_score": ideal_score,
                                    "ideal_failures": failures, "metrics": metrics}
        candidates[identity]["sources"].append(record)
        return identity

    def walk(value, source, attempt, pointer="", depth=0):
        if depth > 8:
            return
        if isinstance(value, dict):
            if "schema_version" in value and "circuits" in value:
                try:
                    validate_submission(value, spec)
                    identifiers = [add(circuit, source, "full_json", attempt, pointer + "/circuits/" + str(index))
                                   for index, circuit in enumerate(value["circuits"])]
                    full_artifacts.append({"path": str(source.relative_to(ROOT)), "attempt": attempt, "json_pointer": pointer,
                                           "standalone_submission": not pointer, "candidates": identifiers})
                    return
                except (ValueError, TypeError, KeyError) as error:
                    rejected.append({"source": str(source.relative_to(ROOT)), "pointer": pointer, "reason": str(error)})
            if "family" in value and "layers" in value:
                try:
                    add(value, source, "family_json", attempt, pointer)
                except (ValueError, TypeError, KeyError) as error:
                    rejected.append({"source": str(source.relative_to(ROOT)), "pointer": pointer, "reason": str(error)})
                return
            for key, child in value.items():
                if isinstance(child, (dict, list)):
                    walk(child, source, attempt, pointer + "/" + str(key), depth + 1)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, (dict, list)):
                    walk(child, source, attempt, pointer + "/" + str(index), depth + 1)

    for attempt in ATTEMPTS:
        directory = ROOT / "attempts" / attempt
        for relative in before[attempt]["current_sha256"]:
            path = directory / relative
            if path.suffix == ".json":
                inspected.append(str(path.relative_to(ROOT)))
                try:
                    value, _ = load_json(path)
                    walk(value, path, attempt)
                except (ValueError, OSError, TypeError) as error:
                    rejected.append({"source": str(path.relative_to(ROOT)), "reason": str(error)})
            elif path.suffix in (".best", ".robust", ".seed", ".txt", ".raw", ".circuit"):
                inspected.append(str(path.relative_to(ROOT)))
                try:
                    circuit = parse_text_circuit(path, spec["families"])
                    if circuit is not None:
                        add(circuit, path, "decoded_numeric_circuit", attempt)
                except (ValueError, OSError, StopIteration, UnicodeError) as error:
                    rejected.append({"source": str(path.relative_to(ROOT)), "reason": str(error)})
    private = ROOT / "adversary/generation_3/private"
    for path in sorted(private.rglob("*.json")):
        if any(parent.is_symlink() for parent in path.parents if parent != ROOT):
            continue
        try:
            value, _ = load_json(path)
            walk(value, path, None)
        except (ValueError, OSError, TypeError):
            continue
    champion = ROOT / "champions/generation_2/artifact.json"
    value, _ = load_json(champion)
    walk(value, champion, None)
    print("INVENTORY", len(inspected), "fresh files;", len(candidates), "unique family circuits", flush=True)

    witness_checks = []
    fresh_reports = {}
    for attempt in ATTEMPTS:
        report_path = ROOT / "attempts" / (attempt + "_audit") / "evaluation.json"
        report, _ = load_json(report_path)
        artifact_path = ROOT / "attempts" / attempt / "artifact.json"
        artifact, artifact_hash = load_json(artifact_path)
        assert artifact_hash == report["artifact_sha256"] == before[attempt]["deadline_sha256"]["artifact.json"]
        assert report["spec_sha256"] == spec_hash
        fresh_reports[attempt] = {"source": str(report_path.relative_to(ROOT)), "source_sha256": digest(report_path),
                                  "core_score": report["core_score"], "valid": report["valid"], "passed": report["passed"],
                                  "artifact_sha256": artifact_hash, "families": {}}
        for name, result in report["families"].items():
            circuit = next(entry for entry in artifact["circuits"] if entry["family"] == name)
            witness = result["fault_robustness"]["worst_witness"]
            output = scalar(families[name]["n"], circuit["layers"], witness["input"], witness["omissions"], witness["direction"] == "inverse")
            recovered = scalar(families[name]["n"], circuit["layers"], output, witness["omissions"], witness["direction"] != "inverse")
            assert len(output) == witness["output_weight"] < 3
            assert sorted(recovered, key=lambda entry: entry["qubit"]) == sorted(witness["input"], key=lambda entry: entry["qubit"])
            witness_checks.append({"attempt": attempt, "family": name, "official_witness": witness,
                                   "independent_scalar_output": output, "opposite_direction_recovered_input": recovered,
                                   "verified_both_directions": True})
            fresh_reports[attempt]["families"][name] = {"ideal_score": result["ideal_score"], "core_score": result["core_score"],
                "minimum": result["fault_robustness"]["minimum"], "resources": result["resources"],
                "failed_scenarios_by_order": {order: entry["failed_scenarios"] for order, entry in result["fault_robustness"]["by_omission_count"].items()}}
    write("fresh_official_findings.json", fresh_reports)
    write("independent_scalar_witnesses.json", witness_checks)
    provenance = json.loads((private / "provenance.json").read_text())
    assert digest(private / "search") == provenance["binary_sha256"]
    assert digest(private / "search.cpp") == provenance["adapted_sha256"]
    for family in spec["families"]:
        target = family["targets"]
        header = [family["id"], family["n"], family["max_rounds"], family["max_cx"], target["min_single"], target["min_double"],
                  target["mean_single_milli"] / 1000, target["mean_double_milli"] / 1000, len(family["edges"])]
        text = " ".join(map(str, header)) + "\n" + "\n".join(" ".join(map(str, edge)) for edge in family["edges"]) + "\n"
        (WORK / (family["id"] + ".cfg")).write_text(text)

    def screen(item):
        identity, candidate = item
        family = families[candidate["family"]]
        edge_ids = {tuple(sorted(edge)): index for index, edge in enumerate(family["edges"])}
        layers = candidate["circuit"]["layers"] + [{"local": ["I"] * family["n"], "cx": []}] * (family["max_rounds"] - len(candidate["circuit"]["layers"]))
        lines = []
        for layer in layers:
            fields = [WORDS.index(word) for word in layer["local"]] + [len(layer["cx"])]
            for gate in layer["cx"]:
                fields.extend(gate + [edge_ids[tuple(sorted(gate))]])
            lines.append(" ".join(map(str, fields)))
        raw = WORK / (identity + ".raw")
        raw.write_text("\n".join(lines) + "\n")
        completed = subprocess.run([str(private / "search"), str(WORK / (family["id"] + ".cfg")), "unused", "0", "0", str(raw)],
                                   cwd=WORK, env=ENV, check=True, capture_output=True, text=True, timeout=60)
        fields = {key: float(value) for key, value in re.findall(r"(\w+)=([0-9.e+-]+)", completed.stdout)}
        native_score = fields["score"]
        score = min(candidate["ideal_score"], native_score)
        passed = not candidate["ideal_failures"] and fields["faults"] == 0
        return identity, {"fields": fields, "stdout": completed.stdout, "passed": passed, "core_score_rounded_native": score,
                          "verification": "trusted private exact up-to-three forward checker; inverse low-weight exclusion equivalent; public ideal scorer independently checked"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for count, (identity, result) in enumerate(pool.map(screen, candidates.items()), 1):
            candidates[identity]["screen"] = result
            if count % 20 == 0:
                print("SCREENED", count, "of", len(candidates), flush=True)
    for entry in full_artifacts:
        entry["passed_all_families"] = all(candidates[identity]["screen"]["passed"] for identity in entry["candidates"])
    passing = {name: [identity for identity, candidate in candidates.items() if candidate["family"] == name and candidate["screen"]["passed"]]
               for name in families}
    best = {name: max((identity for identity, candidate in candidates.items() if candidate["family"] == name),
                     key=lambda identity: (candidates[identity]["screen"]["core_score_rounded_native"], candidates[identity]["ideal_score"],
                                           -candidates[identity]["screen"]["fields"]["failed_scenarios"])) for name in families}
    portfolio = None
    if all(passing.values()):
        selected = {name: identifiers[0] for name, identifiers in passing.items()}
        write("portfolio_artifact.json", {"schema_version": 1, "circuits": [candidates[selected[name]]["circuit"] for name in families]})
        command = [sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), "--submission", str(WORK / "portfolio_artifact.json"),
                   "--output", str(WORK / "portfolio_official_report.json")]
        result = subprocess.run(command, cwd=WORK, env=ENV, check=True, capture_output=True, text=True, timeout=360)
        official = json.loads(result.stdout)
        portfolio = {"selected": selected, "official_passed": official["passed"], "official_core_score": official["core_score"],
                     "artifact": "portfolio_artifact.json", "official_report": "portfolio_official_report.json"}
    after = fingerprint_audit()
    write("fingerprints_after.json", after)
    manifest = json.loads((ROOT / "evaluator/hidden/freeze_manifest.json").read_text())
    trusted = {path: digest(ROOT / path) == checksum for path, checksum in manifest["trusted_source_sha256"].items()}
    write("candidate_inventory.json", {"inspected_fresh_files": inspected, "rejected": rejected, "candidates": candidates, "full_artifacts": full_artifacts})
    summary = {"generation": 3, "no_new_optimization": True, "no_fresh_final_evaluations_duplicated": True,
               "spec_sha256": spec_hash, "runtime_seconds": time.monotonic() - started,
               "deadline_fingerprints_unchanged_before_and_after": all(before[name]["unchanged"] and after[name]["unchanged"] for name in ATTEMPTS),
               "participant_unchanged": all(after[name]["participant_current_matches_launch"] for name in ATTEMPTS),
               "trusted_source_hashes_unchanged": all(trusted.values()), "trusted_hash_checks": trusted,
               "fresh_official_reports": fresh_reports, "independent_failure_witnesses": len(witness_checks),
               "unique_family_candidates_screened": len(candidates), "fresh_files_inspected": len(inspected),
               "passing_family_candidates": passing, "best_candidates": {name: {"id": identity, **candidates[identity]} for name, identity in best.items()},
               "complete_standalone_fresh_witnesses": [entry for entry in full_artifacts if entry["attempt"] and entry["standalone_submission"] and entry["passed_all_families"]],
               "portfolio": portfolio, "solvability": "demonstrated" if portfolio and portfolio["official_passed"] else "unknown",
               "eligibility_note": "Standalone schema-valid deadline files are direct fresh submissions. Family-only JSON and decoded numeric checkpoints are components, not direct full submissions; they are included in portfolio screening. No participant executables were run.",
               "trusted_native_checker_binary_sha256": provenance["binary_sha256"], "maximum_screening_workers": 3}
    write("summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("runtime_seconds", "deadline_fingerprints_unchanged_before_and_after", "participant_unchanged", "trusted_source_hashes_unchanged",
                                                 "unique_family_candidates_screened", "fresh_files_inspected", "passing_family_candidates", "solvability")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
