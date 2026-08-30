import json
import math
import os
from pathlib import Path
import tempfile
import time

import numpy as np

from .model import Episode, FAMILIES, SHAPES, LIMITS, ProtocolError, depolarizing_probabilities
from .transport import SessionError, aggregate, launch_command, run_episode, snapshot_submission, strict_json


def self_check(isolation="bwrap"):
    started = time.monotonic()
    results = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        results.append({"check": name, "passed": True})

    def rejects(function):
        try:
            function()
        except (ValueError, TypeError, OSError):
            return True
        return False

    for qubits in (1, 2, 4, 16, 20, 25):
        for contrast in (0.0, 0.58, 0.95, 1.0):
            for rate in (0.0, 0.001, 0.1, 2.0):
                for depth in (0, 2, 64, 256):
                    success, other = depolarizing_probabilities(qubits, contrast, rate, depth)
                    normalization = success + (2 ** qubits - 1) * other
                    if not 0 <= success <= 1 or not 0 <= other <= 1 or abs(normalization - 1) > 2e-15:
                        raise AssertionError("probability_normalization")
    check("normalized_nonnegative_full_bitstring_distribution_1536_cases", True)
    check("perfect_zero_noise", depolarizing_probabilities(25, 1.0, 0.0, 256) == (1.0, 0.0))
    check("zero_contrast_uniform", depolarizing_probabilities(16, 0.0, 0.4, 256) == (2 ** -16, 2 ** -16))
    check("nonzero_noise_decay", depolarizing_probabilities(20, 1.0, 0.1, 20)[0] <
          depolarizing_probabilities(20, 1.0, 0.1, 2)[0] < 1)
    episode = Episode(731, "spam_drift", (4, 4))
    check("family_id_disclosed", episode.hello()["family"] == "spam_drift")
    check("target_count_unique", len(set(map(tuple, episode.targets))) == 96)
    check("targets_strictly_unqueryable", all(len(matching) == 7 for matching in episode.targets))
    for matching in episode.targets:
        episode.grid.validate_matching(matching, 8)
    check("target_matchings_native_disjoint", True)
    check("spam_always_physical", all(0.58 < episode.contrast(matching, context) < 0.95
          for matching in ([], [0], episode.targets[0]) for context in np.linspace(0, 1, 21)))
    for family in FAMILIES:
        for shape in SHAPES:
            current = Episode(721 + 1009 * FAMILIES.index(family) + 53 * SHAPES.index(shape), family, shape)
            check("support_range_" + family + str(shape),
                  round(0.30 * len(current.grid.edges)) - 1 <= np.count_nonzero(current.crosstalk) <=
                  round(0.30 * len(current.grid.edges)) + 2)
            if family == "distant_pairs":
                check("distant_support_" + str(shape), all(current.grid.distances[current.crosstalk > 0] >= 3))
    template = {"type": "experiment", "matching": [], "depth": 2, "shots": 32}
    invalid = [None, [], {}, {"type": "unknown"}, {**template, "depth": 1},
               {**template, "depth": True}, {**template, "shots": False},
               {**template, "shots": 0}, {**template, "shots": 4097},
               {**template, "matching": [-1]}, {**template, "matching": [0, 0]},
               {**template, "matching": [1, 0]}, {**template, "matching": [0, 1]},
               {**template, "matching": [True]}, {**template, "depth": 258},
               {**template, "extra": 7}, {"type": "final", "predictions": []}]
    initial_state = episode.shots_used, episode.experiments
    check("invalid_requests_rejected", all(rejects(lambda message=message: episode.handle(message)) for message in invalid))
    check("invalid_requests_do_not_mutate_budgets", initial_state == (episode.shots_used, episode.experiments))
    episode.shots_used = LIMITS["shots_budget"] - 32
    response = episode.handle(template)
    check("exact_shot_budget_allowed", response["shots_remaining"] == 0)
    check("shot_budget_bypass_denied", rejects(lambda: episode.handle(template)))
    episode.shots_used = 0
    episode.experiments = LIMITS["max_experiments"]
    check("request_budget_bypass_denied", rejects(lambda: episode.handle(template)))
    episode.handle({"type": "ready"})
    check("post_reveal_queries_denied", rejects(lambda: episode.handle(template)))
    check("duplicate_ready_denied", rejects(lambda: episode.handle({"type": "ready"})))
    for value in (float("nan"), float("inf"), -0.1, 1.1, True, "0.1"):
        check("invalid_prediction_" + str(value), rejects(lambda value=value: episode.handle(
            {"type": "final", "predictions": [value] * 96})))
    exact = [episode.error_rate(matching) for matching in episode.targets]
    episode.handle({"type": "final", "predictions": exact})
    check("oracle_prediction_score_one", episode.metrics()["score"] == 1.0)
    episode.idle = 0.0
    episode.base.fill(0.0)
    episode.crosstalk.fill(0.0)
    check("zero_layer_noise_has_zero_infidelity", all(episode.error_rate(matching) == 0 for matching in episode.targets))
    for text in ('{"type":"ready","type":"experiment"}', '{"value":NaN}', '{"value":Infinity}', "not json"):
        check("invalid_json_" + text[:24], rejects(lambda text=text: strict_json(text)))
    sampler = np.random.default_rng(43)
    probability = depolarizing_probabilities(16, 0.8, 0.05, 20)[0]
    observed = sampler.binomial(1000, probability, size=2000).mean() / 1000
    check("binomial_mean_within_six_sigma", abs(observed - probability) < 6 * math.sqrt(probability * (1-probability) / 2000000))
    hidden = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="selfcheck-", dir=hidden) as directory:
        directory = Path(directory)
        submission = directory / "artifact"
        submission.mkdir()
        policy = submission / "policy.py"
        numerical_smoke = "import numpy as np\nfrom scipy.optimize import minimize, lsq_linear\nfrom scipy.special import expit\nassert np.allclose(np.linalg.solve(np.eye(2), np.ones(2)), np.ones(2))\nassert minimize(lambda values: (float(np.dot(values, values)), 2*values), np.ones(2), jac=True).success\nassert lsq_linear(np.eye(2), np.ones(2)).success\nassert expit(0.) == .5\n"
        policy.write_text(numerical_smoke + "import json,sys\nhello=json.loads(sys.stdin.readline())\nprint(json.dumps({'type':'ready'}),flush=True)\ntargets=json.loads(sys.stdin.readline())\nprint(json.dumps({'type':'final','predictions':[0.01]*len(targets['matchings'])}),flush=True)\nsys.stdin.readline()\n")
        symlink = submission / "leak"
        symlink.symlink_to(hidden / "model.py")
        check("malicious_symlink_rejected", rejects(lambda: snapshot_submission(submission, directory / "bad", "policy.py")))
        symlink.unlink()
        linked = submission / "hardlink.py"
        os.link(policy, linked)
        check("hardlink_rejected", rejects(lambda: snapshot_submission(submission, directory / "bad2", "policy.py")))
        linked.unlink()
        check("policy_path_traversal_rejected", rejects(lambda: snapshot_submission(submission, directory / "bad3", "../model.py")))
        snapshot = directory / "snapshot"
        snapshot_submission(submission, snapshot, "policy.py")
        command = launch_command(snapshot, "policy.py", isolation)
        current = Episode(812, "local_clusters", (4, 4))
        record = run_episode(current, command, snapshot, directory / "valid.stderr", isolation=isolation)
        check("subprocess_handshake_and_clean_exit", record["valid"])
        check("isolated_numpy_scipy_blas_lapack_smoke", record["valid"])
        check("public_greeting_has_no_private_state", not any(key in current.hello() for key in
              ("seed", "seed_hex", "base", "crosstalk", "idle", "spam_edges", "targets", "truths")))
        denied_paths = [str(hidden / "benchmark.json"), str(hidden / "model.py"),
                        "/proc/" + str(os.getpid()) + "/root" + str(hidden / "model.py")]
        probes = "import pathlib\nfor target in " + repr(denied_paths) + ":\n    try:\n        pathlib.Path(target).read_bytes()\n    except OSError:\n        pass\n    else:\n        raise RuntimeError('oracle_path_readable')\n"
        probes += "try:\n    import hidden.model\nexcept ImportError:\n    pass\nelse:\n    raise RuntimeError('oracle_module_importable')\n"
        if isolation == "bwrap":
            policy.write_text(probes + policy.read_text())
            oracle_snapshot = directory / "oracle_snapshot"
            snapshot_submission(submission, oracle_snapshot, "policy.py")
            oracle_record = run_episode(Episode(814, "distant_pairs", (4, 4)),
                                        launch_command(oracle_snapshot, "policy.py", isolation),
                                        oracle_snapshot, directory / "oracle.stderr", isolation=isolation)
            check("hidden_path_parent_proc_and_module_denied", oracle_record["valid"])
        failures = {
            "malformed_json_process": "import sys\nsys.stdin.readline()\nprint('broken',flush=True)\n",
            "oversized_message_process": "import sys\nsys.stdin.readline()\nprint('x'*40000,flush=True)\n",
            "overspend_process": "import sys,json\nsys.stdin.readline()\nprint(json.dumps({'type':'experiment','matching':[],'depth':2,'shots':240001}),flush=True)\n",
            "negative_budget_bypass_process": "import sys,json\nsys.stdin.readline()\nprint(json.dumps({'type':'experiment','matching':[],'depth':2,'shots':-32}),flush=True)\n",
        }
        for name, program in failures.items():
            policy.write_text(program)
            failure_snapshot = directory / name
            snapshot_submission(submission, failure_snapshot, "policy.py")
            failure_record = run_episode(Episode(817, "local_clusters", (4, 4)),
                                         launch_command(failure_snapshot, "policy.py", isolation),
                                         failure_snapshot, directory / (name + ".stderr"), isolation=isolation)
            check(name, not failure_record["valid"] and failure_record["shots_used"] == 0)
    record.update(family="local_clusters", normalized_mse=0.0, valid=True)
    check("audit_mode_never_certifies", not aggregate([record], isolated=False)["passed"])
    return {"passed": True, "self_checks_passed": len(results), "isolation": isolation,
            "wall_seconds": time.monotonic() - started, "checks": results}
