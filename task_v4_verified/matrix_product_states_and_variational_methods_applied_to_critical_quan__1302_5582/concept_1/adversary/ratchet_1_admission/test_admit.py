"""Mock/temporary-fixture tests only; no production modules or solvers execute."""

import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import admit


INFRA_CERTIFICATE_PATH = Path("adversary/wall_guard_repair") / (
    "freeze_manifest_v%d.json" % admit.INFRASTRUCTURE_REVISION)


def request(index=0):
    length = 32
    return {"version": 1, "case_id": "source-" + str(index), "seed": index,
            "n_sites": length, "local_dim": 8, "bond_cap": 12, "sector": "any",
            "omega": [0.8] * length, "mass2": [-0.10 + index * 0.001] * length,
            "lambda4": [0.1] * length, "field": [0.0] * length,
            "coupling": [0.7] * (length - 1)}


def measurement(energy=2.0):
    return {"energy": energy, "parity": 1.0, "max_bond": 1, "norm_after_canonicalization": 1.0}


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else admit.encoded(value))
        return path

    def proposal(self):
        self.write("references/state.npz", b"mock state, never loaded by numpy")
        return {"cases": [{"family": "family-" + str(index // 2), "request": request(index),
                           "reference_state": "references/state.npz", "reference_energy": 1.0,
                           "source_case_id": "source-" + str(index)} for index in range(8)],
                "search_summary": {"mock": True}}

    def preparation(self):
        for relative in admit.RUNTIME_SOURCES:
            self.write(relative, b"mock trusted source")
        hashes = {}
        for name in admit.PRODUCTION:
            for directory in ("champions/generation_1/submission", "participant/baseline", "participant/workspace"):
                self.write(directory + "/" + name, ("mock " + name).encode())
            hashes[name] = admit.sha256(self.root / "participant/baseline" / name)
        self.write("participant/input/scoring.json", {"version": 2, "case_count": 8, "family_count": 4,
                   "frozen_before_generation_fresh_agent_launch": True, "target": admit.TARGET, "stages": admit.STAGES})
        preparation = {"generation": 1, "production_source": "champions/generation_1/submission",
                       "production_sha256": hashes, "private_development_artifacts_released": False,
                       "fresh_attempts_for_this_generation_launched": 0, "target_predeclared": admit.TARGET,
                       "stages": admit.STAGES}
        self.write(admit.WORK / "public_preparation.json", preparation)
        self.write("evaluator/hidden/calibration.json", {"version": 1, "infrastructure_revision": 3,
                                                       "frozen_hashes": {}})
        self.write(INFRA_CERTIFICATE_PATH,
                   {"infrastructure_revision": admit.INFRASTRUCTURE_REVISION,
                    "checks_passed": 15, "fresh_attempts_launched": 0,
                    "source_sha256": {relative: admit.sha256(self.root / relative) for relative in
                                      ("evaluator/sandbox_runner.py", "evaluator/worker.py")}})
        return preparation

    def test_valid_request_and_closed_endpoints(self):
        for key, bounds in admit.BOUNDS.items():
            for endpoint in bounds:
                candidate = request()
                candidate[key] = [endpoint] * len(candidate[key])
                self.assertEqual(admit.validate_request(candidate), candidate)
        for length, dimension, cap in ((32, 8, 12), (64, 14, 24)):
            candidate = request()
            candidate.update(n_sites=length, local_dim=dimension, bond_cap=cap)
            for key in admit.BOUNDS:
                candidate[key] = [candidate[key][0]] * (length - (key == "coupling"))
            admit.validate_request(candidate)

    def test_reject_bounds_nonfinite_boolean_and_lengths(self):
        for key in admit.BOUNDS:
            for value in (float("nan"), float("inf"), True, admit.BOUNDS[key][0] - 0.001,
                          admit.BOUNDS[key][1] + 0.001):
                with self.subTest(key=key, value=value):
                    candidate = request()
                    candidate[key][0] = value
                    with self.assertRaises(admit.AdmissionError):
                        admit.validate_request(candidate)
            candidate = request()
            candidate[key].pop()
            with self.assertRaises(admit.AdmissionError):
                admit.validate_request(candidate)
        for key, value in (("version", 2), ("version", True), ("seed", -1), ("seed", 1.5),
                           ("seed", False), ("n_sites", 31), ("n_sites", 65), ("local_dim", 15),
                           ("bond_cap", 11), ("bond_cap", 25), ("sector", "ground")):
            candidate = request()
            candidate[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(admit.AdmissionError):
                admit.validate_request(candidate)

    def test_sector_fields_and_unknown_or_budget_fields(self):
        for sector in ("even", "odd"):
            candidate = request()
            candidate["sector"] = sector
            admit.validate_request(candidate)
            candidate["field"][0] = 1e-10
            with self.assertRaises(admit.AdmissionError):
                admit.validate_request(candidate)
        for key in ("budget_seconds", "wall_seconds", "extra"):
            candidate = dict(request(), **{key: 6})
            with self.assertRaises(admit.AdmissionError):
                admit.validate_request(candidate)

    def test_identity_excludes_only_ids_seeds_and_budgets(self):
        original = request()
        changed = dict(original, case_id="renamed", seed=123, budget_seconds=40, wall_seconds=120)
        self.assertEqual(admit.objective_identity(original), admit.objective_identity(changed))
        for key, value in (("bond_cap", 13), ("local_dim", 9), ("sector", "odd")):
            self.assertNotEqual(admit.objective_identity(original),
                                admit.objective_identity(dict(original, **{key: value})))
        changed = copy.deepcopy(original)
        changed["omega"][0] += 0.01
        self.assertNotEqual(admit.objective_identity(original), admit.objective_identity(changed))
        changed = copy.deepcopy(original)
        changed["field"] = [-0.0] * original["n_sites"]
        self.assertEqual(admit.objective_identity(original), admit.objective_identity(changed))

    def test_proposal_stable_opaque_ids_preserve_parameters(self):
        proposal = self.proposal()
        original = copy.deepcopy(proposal)
        records = admit.validate_proposal(proposal, [], self.root)
        self.assertEqual(proposal, original)
        self.assertEqual(len(records), 8)
        for record in records:
            source = next(entry for entry in original["cases"] if entry["source_case_id"] == record["source_case_id"])
            restored = dict(record["request"], case_id=source["request"]["case_id"])
            self.assertEqual(restored, source["request"])
            self.assertTrue(record["request"]["case_id"].startswith("g1_"))
        proposal["cases"].reverse()
        self.assertEqual(records, admit.validate_proposal(proposal, [], self.root))

    def test_duplicates_families_counts_and_public_overlap(self):
        proposal = self.proposal()
        proposal["cases"][1]["request"] = dict(proposal["cases"][0]["request"], case_id="different", seed=888)
        with self.assertRaisesRegex(admit.AdmissionError, "duplicate"):
            admit.validate_proposal(proposal, [], self.root)
        proposal = self.proposal()
        proposal["cases"][1]["request"] = dict(proposal["cases"][0]["request"], bond_cap=13)
        admit.validate_proposal(proposal, [], self.root)
        for change in ("count", "family"):
            proposal = self.proposal()
            if change == "count":
                proposal["cases"].pop()
            else:
                proposal["cases"][0]["family"] = "other"
            with self.assertRaises(admit.AdmissionError):
                admit.validate_proposal(proposal, [], self.root)
        proposal = self.proposal()
        public = dict(proposal["cases"][0]["request"], seed=999, case_id="public", budget_seconds=6, wall_seconds=30)
        with self.assertRaisesRegex(admit.AdmissionError, "overlaps"):
            admit.validate_proposal(proposal, [public], self.root)

    def test_unsafe_reference_paths(self):
        for path in ("../state.npz", "/tmp/state.npz"):
            proposal = self.proposal()
            proposal["cases"][0]["reference_state"] = path
            with self.assertRaises(admit.AdmissionError):
                admit.validate_proposal(proposal, [], self.root)
        self.write("outside.npz", b"fixture")
        (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(admit.AdmissionError):
            admit.contained(self.root, "linked/outside.npz", regular=True)

    def test_strict_json(self):
        for payload in (b'{"seed":0,"seed":1}', b'{"energy":NaN}', b'{"energy":1e999}'):
            path = self.write("bad.json", payload)
            with self.assertRaises(ValueError):
                admit.read_json(path)

    def test_preparation_source_hashes_target_and_budgets(self):
        preparation = self.preparation()
        before = admit.immutable_inputs(self.root)
        self.assertIn("participant/workspace/optimizer.py", before)
        self.assertIn("adversary/ratchet_1_admission/admit.py", before)
        self.assertIn(str(INFRA_CERTIFICATE_PATH), before)
        self.assertEqual(admit.read_json(self.root / "evaluator/hidden/calibration.json")["infrastructure_revision"], 3)
        self.write("participant/baseline/solve.py", b"tampered")
        with self.assertRaisesRegex(admit.AdmissionError, "hash mismatch"):
            admit.immutable_inputs(self.root)
        preparation = self.preparation()
        preparation["target_predeclared"] = dict(admit.TARGET, score_min=79)
        self.write(admit.WORK / "public_preparation.json", preparation)
        with self.assertRaisesRegex(admit.AdmissionError, "target changed"):
            admit.immutable_inputs(self.root)
        preparation = self.preparation()
        preparation["stages"] = copy.deepcopy(admit.STAGES)
        preparation["stages"]["short"]["cpu_seconds"] = 7
        self.write(admit.WORK / "public_preparation.json", preparation)
        with self.assertRaisesRegex(admit.AdmissionError, "budgets changed"):
            admit.immutable_inputs(self.root)
        manifest_path = INFRA_CERTIFICATE_PATH
        for key, value in (("infrastructure_revision", admit.INFRASTRUCTURE_REVISION - 1),
                           ("checks_passed", 13), ("fresh_attempts_launched", 1)):
            with self.subTest(manifest_field=key):
                self.preparation()
                manifest = admit.read_json(self.root / manifest_path)
                manifest[key] = value
                self.write(manifest_path, manifest)
                with self.assertRaises(admit.AdmissionError):
                    admit.immutable_inputs(self.root)
        self.preparation()
        manifest = admit.read_json(self.root / manifest_path)
        manifest["source_sha256"]["evaluator/worker.py"] = "0" * 64
        self.write(manifest_path, manifest)
        with self.assertRaises(admit.AdmissionError):
            admit.immutable_inputs(self.root)

    def test_cache_fingerprint_covers_exact_request_production_runtime(self):
        candidate = dict(request(), budget_seconds=6, wall_seconds=30)
        original = admit.cache_key(candidate, {"solve.py": "one"}, {"worker.py": "two"}, {"numpy": "x"})
        self.assertEqual(original, admit.cache_key(copy.deepcopy(candidate), {"solve.py": "one"},
                                                  {"worker.py": "two"}, {"numpy": "x"}))
        for changed in (dict(candidate, seed=99), dict(candidate, case_id="new"),
                        dict(candidate, budget_seconds=40), dict(candidate, wall_seconds=120)):
            self.assertNotEqual(original, admit.cache_key(changed, {"solve.py": "one"}, {"worker.py": "two"}, {"numpy": "x"}))
        self.assertNotEqual(original, admit.cache_key(candidate, {"solve.py": "changed"}, {"worker.py": "two"}, {"numpy": "x"}))
        self.assertNotEqual(original, admit.cache_key(candidate, {"solve.py": "one"}, {"worker.py": "changed"}, {"numpy": "x"}))
        self.assertNotEqual(original, admit.cache_key(candidate, {"solve.py": "one"}, {"worker.py": "two"}, {"numpy": "changed"}))

    def test_process_and_reference_measurement_schema(self):
        candidate = dict(request(), budget_seconds=6, wall_seconds=30)
        valid = {"process_valid": True, "cpu_accounted": True, "returncode": 0,
                 "timed_out": False, "outer_timed_out": False, "cpu_seconds": 1.0,
                 "wall_seconds": 2.0, "wall_accounting": admit.WALL_ACCOUNTING}
        admit.validate_process(valid, candidate)
        for key, value in (("cpu_seconds", 6.1), ("wall_seconds", 30.1), ("returncode", False),
                           ("timed_out", True), ("outer_timed_out", True), ("cpu_accounted", False),
                           ("wall_seconds", "0"), ("cpu_seconds", float("nan"))):
            with self.subTest(key=key), self.assertRaises(ValueError):
                admit.validate_process(dict(valid, **{key: value}), candidate)
        admit.validate_measurement(measurement(), request())
        with self.assertRaises(admit.AdmissionError):
            admit.validate_measurement(measurement(), dict(request(), sector="odd"))
        with self.assertRaises(admit.AdmissionError):
            admit.validate_measurement(dict(measurement(), max_bond=13), request())

    def test_normal_exit_over_budget_is_rejected_despite_grace(self):
        for stage, budget in admit.STAGES.items():
            with self.subTest(stage=stage):
                candidate = dict(request(), budget_seconds=budget["cpu_seconds"],
                                 wall_seconds=budget["wall_seconds"])
                result = {"process_valid": True, "cpu_accounted": True, "returncode": 0,
                          "timed_out": False, "outer_timed_out": False,
                          "cpu_seconds": budget["cpu_seconds"],
                          "wall_seconds": budget["cpu_seconds"] + 1.5,
                          "wall_accounting": admit.WALL_ACCOUNTING}
                admit.validate_process(result, candidate)
                result["cpu_seconds"] = budget["cpu_seconds"] + 1.0
                with self.assertRaisesRegex(admit.AdmissionError, "baseline CPU"):
                    admit.validate_process(result, candidate)

    def test_both_gaps_strictly_above_floor(self):
        reference = measurement(0.0)
        baselines = {"short": measurement(1e-4), "long": measurement(2e-4)}
        self.assertEqual(set(admit.improvement_gaps(baselines, reference, 32)), set(admit.STAGES))
        for energy in (0, -1e-4, 32e-7):
            invalid = dict(baselines, short=measurement(energy))
            with self.assertRaises(admit.AdmissionError):
                admit.improvement_gaps(invalid, reference, 32)

    def test_mock_cold_stage_resume_and_no_retry_failure(self):
        inputs = {"participant/baseline/" + name: name for name in admit.PRODUCTION}
        candidate = dict(request(), budget_seconds=6, wall_seconds=30)
        contractor = SimpleNamespace(load_mps=Mock(return_value="mock tensors"), measure=Mock(return_value=measurement()))

        def execute(submission, participant, scratch, requested):
            scratch.mkdir(parents=True)
            (scratch / "state.npz").write_bytes(b"mock NPZ, never parsed by numpy")
            return {"process_valid": True, "cpu_accounted": True, "returncode": 0,
                    "timed_out": False, "outer_timed_out": False, "cpu_seconds": 1.0,
                    "wall_seconds": 2.0, "wall_accounting": admit.WALL_ACCOUNTING,
                    "state_path": str(scratch / "state.npz")}

        runner = SimpleNamespace(run_submission=Mock(side_effect=execute))
        first = admit.cold_stage(self.root, candidate, inputs, {}, runner, contractor)
        second = admit.cold_stage(self.root, candidate, inputs, {}, runner, contractor)
        self.assertEqual(first, second)
        self.assertEqual(runner.run_submission.call_count, 1)
        self.assertEqual(contractor.measure.call_count, 2)
        failed = dict(candidate, seed=999)
        runner.run_submission.side_effect = RuntimeError("mock infrastructure failure")
        with self.assertRaisesRegex(admit.AdmissionError, "retained"):
            admit.cold_stage(self.root, failed, inputs, {}, runner, contractor)
        with self.assertRaisesRegex(admit.AdmissionError, "no automatic retry"):
            admit.cold_stage(self.root, failed, inputs, {}, runner, contractor)
        self.assertEqual(runner.run_submission.call_count, 2)

    def test_incomplete_or_tampered_cache_does_not_execute(self):
        candidate = dict(request(), budget_seconds=6, wall_seconds=30)
        inputs = {"participant/baseline/" + name: name for name in admit.PRODUCTION}
        production = {name: inputs["participant/baseline/" + name] for name in admit.PRODUCTION}
        identity = admit.cache_key(candidate, production, inputs, {})
        location = self.root / admit.WORK / "baseline_cache" / identity
        location.mkdir(parents=True)
        runner = SimpleNamespace(run_submission=Mock())
        with self.assertRaisesRegex(admit.AdmissionError, "interrupted"):
            admit.cold_stage(self.root, candidate, inputs, {}, runner, None)
        self.write(location.relative_to(self.root) / "checkpoint.json", {"status": "complete", "fingerprint": "wrong"})
        with self.assertRaisesRegex(admit.AdmissionError, "fingerprint"):
            admit.cold_stage(self.root, candidate, inputs, {}, runner, None)
        runner.run_submission.assert_not_called()


if __name__ == "__main__":
    unittest.main()
