"""Regenerate source snapshots, hidden requests, references, and score evidence.

Run with the supplied CPU runtime. Only this pilot directory is written.
The local source repository is read with git-show; no checkout is modified.
"""

import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OLD = "fa7058d6f710c60976ba1330ae6ed9ec2ef705d9"
FIXED = "f476c5b4a3d51cb4b2883a17cef8bd5501f211cd"


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def source(repository, revision, path):
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=repository, text=True
    )


def definition(text, name):
    for node in ast.parse(text).body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name:
            return "\n".join(text.splitlines()[node.lineno - 1:node.end_lineno]) + "\n"
    raise ValueError(name)


def snapshot(repository, revision, destination):
    package = destination / "bijx"
    records = {}
    for relative in ("utils.py", "fourier.py", "solvers.py", "bijections/base.py"):
        original = f"src/bijx/{relative}"
        text = source(repository, revision, original)
        write_text(package / relative, text)
        records[relative] = {"upstream_path": original, "selection": "complete module"}
    flow_imports = (
        "import typing as tp\nimport jax\nimport jax.numpy as jnp\n"
        "from ..solvers import odeint_rk4\nfrom .base import Bijection\n\n"
    )
    spectrum_imports = (
        "import jax\nimport jax.numpy as jnp\nfrom flax import nnx\n"
        "from ..fourier import FourierMeta\nfrom ..utils import Const, ShapeInfo\n"
        "from .base import ApplyBijection\n"
    )
    if revision == FIXED:
        spectrum_imports += "from .affine_complex import complex_affine_apply\n"
        relative = "bijections/affine_complex.py"
        write_text(package / relative, source(repository, revision, "src/bijx/" + relative))
        records[relative] = {"upstream_path": "src/bijx/" + relative,
                             "selection": "complete module"}
    for relative, name, imports in (
        ("bijections/continuous.py", "ContFlowRK4", flow_imports),
        ("bijections/fourier.py", "SpectrumScaling", spectrum_imports),
    ):
        original = "src/bijx/" + relative
        text = imports + "\n" + definition(source(repository, revision, original), name)
        write_text(package / relative, text)
        records[relative] = {"upstream_path": original, "selection": f"verbatim class {name}"}
    write_text(package / "__init__.py", "")
    write_text(package / "bijections/__init__.py", "")
    write_text(destination / "LICENSE.bijx", source(repository, revision, "LICENSE"))
    for relative, record in records.items():
        record["sha256"] = hashlib.sha256((package / relative).read_bytes()).hexdigest()
    return {"revision": revision, "files": records}


def make_case(identifier, dimension, times, direction, generator, linear=False, steps=96):
    coefficients = [-0.13, 0.0, 0.0, 0.0] if linear else [
        float(generator.uniform(-0.25, -0.06)),
        float(generator.uniform(0.08, 0.24)),
        float(generator.uniform(-0.18, 0.18)),
        float(generator.uniform(-0.07, 0.07)),
    ]
    return {
        "kind": "flow", "id": identifier, "direction": direction,
        "x": generator.normal(0.0, 0.6, dimension).tolist(),
        "log_density": float(generator.uniform(-2.0, 0.0)), "times": times,
        "parameters": coefficients + generator.uniform(-0.24, 0.31, dimension // 2 + 1).tolist(),
        "cotangent": generator.normal(0.0, 0.5, dimension).tolist(),
        "density_weight": float(generator.uniform(0.2, 0.7)), "steps": steps,
    }


def make_pool(seed, challenge=False):
    import numpy as np

    generator = np.random.default_rng(seed)
    configurations = (
        [(5, [-0.7, 0.15], "forward"), (6, [1.1, -0.35], "inverse"),
         (5, [0.4, 0.4], "inverse"), (6, [-0.6, 4.4], "forward")]
        if challenge else
        [(4, [0.2, 0.85], "forward"), (4, [0.2, 0.85], "inverse"),
         (3, [1.2, -0.4], "forward"), (3, [1.2, -0.4], "inverse"),
         (4, [0.7, 0.7], "forward"), (3, [-0.4, 0.6], "inverse")]
    )
    cases = [make_case(f"flow-{index}", dimension, times, direction, generator,
                       linear=index == 0, steps=384 if abs(times[1]-times[0]) > 3 else 96)
             for index, (dimension, times, direction) in enumerate(configurations)]
    acceptance = make_case("acceptance-0", 4 if not challenge else 5,
                           [-0.3, 1.1] if not challenge else [0.8, -0.5],
                           "forward", generator)
    dimension = len(acceptance["x"])
    acceptance = {key: acceptance[key] for key in ("id", "times", "parameters", "steps")}
    acceptance.update({
        "kind": "acceptance",
        "latents": generator.normal(0.0, 0.85, (7, dimension)).tolist(),
        "uniforms": [0.2, 0.95, 0.7, 0.1, 0.85, 0.4],
    })
    if not challenge:
        acceptance["latents"][2] = [2.6 if index % 2 == 0 else -2.4 for index in range(dimension)]
    return {"version": 1, "cases": cases + [acceptance]}


def assert_success(request, response, label):
    for case in request["cases"]:
        result = response.get("results", {}).get(case["id"], {})
        if not result or "error" in result:
            raise RuntimeError(f"{label}/{case['id']}: {result}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/tmp/ale_bijx"))
    parser.add_argument("--scaffold-only", action="store_true")
    arguments = parser.parse_args()
    evaluator_spec = importlib.util.spec_from_file_location("pilot_evaluator", ROOT / "private/evaluator.py")
    evaluator = importlib.util.module_from_spec(evaluator_spec)
    evaluator_spec.loader.exec_module(evaluator)
    evaluator.limit_affinity()
    os.environ.update(evaluator.constrained_environment())
    participant = ROOT / "participant/workspace"
    weak = ROOT / "private/baselines/weak"
    strong = ROOT / "private/reference/implementation"
    provenance_path = ROOT / "private/provenance.json"
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text())
        for relative, expected in previous.get("participant_initial_sha256", {}).items():
            path = participant / relative
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"refusing to overwrite modified participant source: {relative}")
    old_record = snapshot(arguments.source, OLD, participant)
    snapshot(arguments.source, OLD, weak)
    fixed_record = snapshot(arguments.source, FIXED, strong)
    for destination in (weak, strong):
        for name in ("api.py", "solve.py"):
            write_text(destination / name, (participant / name).read_text())
    initial_hashes = {
        str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(participant.rglob("*")) if path.is_file()
    }
    provenance = {
        "source_repository": "mathisgerdes/bijx", "participant": old_record,
        "official_reference": fixed_record, "participant_initial_sha256": initial_hashes,
        "fixes": {
            "duration": "74828bc91a8107d4dcc3ad91230ef41b40522674",
            "density_sign": "7dd214c47e6cb9e13bcf8c77d954acec146840dc",
        },
        "curation": "Complete support modules plus verbatim target classes; only import lists and package init files are curated. No arithmetic is altered.",
        "runtime": {"python": "3.12", "jax": "0.8.1", "flax": "0.12.1", "diffrax": "0.7.0"},
        "attempts": "No agents or participant attempts launched.",
    }
    save_json(provenance_path, provenance)
    public_example = make_pool(271828)["cases"][0]
    public_example["id"] = "example"
    save_json(ROOT / "participant/input/example.json", {"version": 1, "cases": [public_example]})
    pools = {"standard": make_pool(872013), "challenge": make_pool(923617, challenge=True)}
    for name, request in pools.items():
        save_json(ROOT / "private/challenge_pool" / name / "request.json", request)
    if arguments.scaffold_only:
        print("source snapshots and requests ready", flush=True)
        return
    evidence = {"baseline_runs": {}, "agent_runs": 0,
                "score_formula": "family score = 1 / (1 + normalized_RMSE / scale); scale = max(10*strong_error, sqrt((weak_error+1e-10)*(strong_error+1e-10)), 1e-8). Equal family mean; no pass/fail clipping.",
                "accuracy": "Reference uses official fixed source at four times each requested step count; strong baseline uses the stated count.",
                "memory": "No independent memory bound or memory-score claim; differentiation-through-steps remains an allowed shortcut."}
    for name, request in pools.items():
        print(f"generating {name} official high-accuracy references", flush=True)
        high_request = json.loads(json.dumps(request))
        for case in high_request["cases"]:
            case["steps"] *= 4
        reference, reference_time, _ = evaluator.run_submission(strong, high_request, timeout=600, trusted_reference=True)
        assert_success(request, reference, f"{name}/reference")
        decisions = reference["results"]["acceptance-0"]["accepted"]
        if not any(decisions) or all(decisions):
            raise RuntimeError(f"{name}: acceptance trace must cover acceptance and rejection")
        strong_output, strong_time, _ = evaluator.run_submission(strong, request, timeout=600, trusted_reference=True)
        assert_success(request, strong_output, f"{name}/strong")
        weak_output, weak_time, _ = evaluator.run_submission(weak, request, timeout=600, trusted_reference=True)
        assert_success(request, weak_output, f"{name}/weak")
        strong_errors, _ = evaluator.measure(request, strong_output, reference)
        weak_errors, _ = evaluator.measure(request, weak_output, reference)
        calibration = {
            family: {
                "weak_error": weak_errors[family], "strong_error": strong_errors[family],
                "scale": max(10 * strong_errors[family],
                             math.sqrt((weak_errors[family] + 1e-10) * (strong_errors[family] + 1e-10)),
                             1e-8),
            } for family in evaluator.FAMILIES
        }
        strong_score, strong_families = evaluator.score_errors(strong_errors, calibration)
        weak_score, weak_families = evaluator.score_errors(weak_errors, calibration)
        if strong_score <= 0.9 or min(strong_families.values()) <= 0.9:
            raise RuntimeError(f"official implementation self-score too low: {strong_families}")
        destination = ROOT / "private/challenge_pool" / name
        save_json(destination / "reference.json", reference)
        save_json(destination / "calibration.json", calibration)
        save_json(destination / "weak_outputs.json", weak_output)
        save_json(destination / "strong_outputs.json", strong_output)
        evidence["baseline_runs"][name] = {
            "strong_score": strong_score, "strong_family_scores": strong_families,
            "weak_score": weak_score, "weak_family_scores": weak_families,
            "reference_seconds": reference_time, "strong_seconds": strong_time,
            "weak_seconds": weak_time, "cases": len(request["cases"]),
            "reference_acceptance_decisions": decisions,
        }
        save_json(ROOT / "private/evidence.json", evidence)
        print(f"{name}: strong={strong_score:.6f} weak={weak_score:.6f}", flush=True)
    verification = subprocess.run(
        [sys.executable, str(ROOT / "private/verify_reference.py")],
        cwd=strong, env=evaluator.constrained_environment(), capture_output=True, text=True,
        timeout=300, preexec_fn=evaluator.limit_affinity,
    )
    if verification.returncode:
        raise RuntimeError(verification.stderr + verification.stdout)
    print(verification.stdout, flush=True)
    print("pilot 01 references and calibration ready", flush=True)


if __name__ == "__main__":
    main()
