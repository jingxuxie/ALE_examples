from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT.parents[1] / "private" / "sources"
PUBLIC = ROOT / "participant" / "input"
REFERENCE = ROOT / "private" / "reference"
PYTHON = Path("/tmp/ale_python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12")


def environment():
    result = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        result[key] = "4"
    result.update(JAX_ENABLE_X64="true", JAX_PLATFORMS="cpu", PYTHONDONTWRITEBYTECODE="1")
    result["XLA_FLAGS"] = "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4"
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assets():
    import numpy as np

    for folder in (PUBLIC / "checkpoints", PUBLIC / "examples", REFERENCE / "vendor", ROOT / "attempt"):
        folder.mkdir(parents=True, exist_ok=True)
    package = SOURCES / "continuous-flow-lft" / "jaxlft"
    destination = REFERENCE / "vendor" / "jaxlft"
    destination.mkdir(exist_ok=True)
    hashes = {}
    for source in sorted(package.glob("*.py")):
        text = source.read_text()
        if source.name == "ode.py":
            old = "from jax import core, custom_derivatives, tree_leaves, tree_map"
            assert text.count(old) == 1
            text = text.replace(old, "from jax import core, custom_derivatives\nfrom jax.tree_util import tree_leaves, tree_map")
            text = text.replace("from jax.experimental.ode import ravel_first_arg", "from jax.experimental.ode import ravel_first_arg\nfrom jax._src import api_util")
            text = text.replace("fun = ravel_first_arg(fun, unravel)", "fun = ravel_first_arg(fun, unravel, api_util.debug_info('odeint', fun, args, {}))")
        (destination / source.name).write_text(text)
        hashes["continuous-flow-lft/jaxlft/" + source.name] = digest(source)
    shutil.copyfile(SOURCES / "continuous-flow-lft" / "LICENSE", REFERENCE / "vendor" / "LICENSE.continuous-flow-lft")
    later = SOURCES / "bijx" / "src" / "bijx" / "nn" / "conv.py"
    shutil.copyfile(later, REFERENCE / "vendor" / "later_conv.py")
    hashes["bijx/src/bijx/nn/conv.py"] = digest(later)
    for filename in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        if (SOURCES / "bijx" / filename).is_file():
            shutil.copyfile(SOURCES / "bijx" / filename, REFERENCE / "vendor" / "LICENSE.bijx")
            break
    sys.path.insert(0, str(REFERENCE / "vendor"))
    from jaxlft.convolution import kernel_d4

    manifest = {}
    with zipfile.ZipFile(SOURCES / "phi4_parameters.zip") as archive:
        for model in ("single-L32", "single-L64", "range-L32"):
            raw = archive.read("all-parameters/" + model + ".npz")
            with np.load(io.BytesIO(raw), allow_pickle=True) as checkpoint:
                params = checkpoint["params"].item()
                arrays = dict(params["~"])
                arrays["lam_range"] = checkpoint["lam"]
                if "kernel_gauss" in params:
                    arrays["width_factor"] = params["kernel_gauss"]["width_factor"]
            size = int(model.split("L")[-1])
            count, orbits = kernel_d4((size, size))
            assert count == arrays["w"].shape[0]
            arrays["orbits"] = np.asarray(orbits, dtype=np.int32)
            np.savez(PUBLIC / "checkpoints" / (model + ".npz"), **arrays)
            manifest[model] = {
                "source_size": size,
                "conditional": model.startswith("range"),
                "coupling": arrays["lam_range"].tolist(),
                "arrays": {name: {"shape": list(value.shape), "dtype": str(value.dtype)} for name, value in arrays.items()},
                "original_npz_sha256": hashlib.sha256(raw).hexdigest(),
                "public_npz_sha256": digest(PUBLIC / "checkpoints" / (model + ".npz")),
            }
    (PUBLIC / "models.json").write_text(json.dumps(manifest, indent=2) + "\n")
    provenance = {
        "original_commit": "7b34521cea48f464d0790a4896b2fe86cbfedfa6",
        "parameter_release_commit": "e6bec65",
        "later_commit": "f476c5b4a3d51cb4b2883a17cef8bd5501f211cd",
        "resize_fix": "555423faad970592d63b4b93f16e90f7e9093c92",
        "archive_sha256": digest(SOURCES / "phi4_parameters.zip"),
        "source_sha256": hashes,
        "compatibility": ["ode.py: move tree_leaves/tree_map import to jax.tree_util; provide ravel_first_arg debug_info as current jax.experimental.ode does; no numerical changes"],
    }
    (REFERENCE / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


def cases():
    import numpy as np

    test = [
        ("native32", "single-L32", 32, "native", "probe", .173, 4.572, 2),
        ("native64", "single-L64", 64, "native", "probe", .631, 4.398, 2),
        ("conditional32", "range-L32", 32, "native", "probe", .413, [4.37, 5.61], 2),
        ("transfer64", "range-L32", 64, "transfer", "probe", .277, 5.23, 1),
        ("forward32", "single-L32", 32, "native", "forward", 0., 4.572, 1),
        ("reverse32", "single-L32", 32, "native", "reverse", 0., 4.572, 1),
        ("forward64", "single-L64", 64, "native", "forward", 0., 4.398, 1),
        ("reverse64", "single-L64", 64, "native", "reverse", 0., 4.398, 1),
        ("conditional_forward32", "range-L32", 32, "native", "forward", 0., 4.46, 1),
        ("conditional_reverse64", "range-L32", 64, "transfer", "reverse", 0., 5.54, 1),
    ]
    midpoint = 4.0 + 2.0 * 17.5 / 49
    challenge = [
        ("coupling_transition", "range-L32", 32, "native", "probe", .019, [midpoint - 1e-5, midpoint + 1e-5], 2),
        ("coupling_endpoints64", "range-L32", 64, "transfer", "probe", .977, [4., 6.], 2),
        ("odd_transfer33", "single-L32", 33, "transfer", "probe", .381, 4.572, 2),
        ("odd_transfer63", "range-L32", 63, "transfer", "probe", .827, 4.73, 1),
        ("conditional_reverse32", "range-L32", 32, "native", "reverse", 0., 5.91, 1),
        ("conditional_forward64", "range-L32", 64, "transfer", "forward", 0., 4.09, 1),
        ("heldout_forward64", "single-L64", 64, "native", "forward", 0., 4.398, 1),
        ("heldout_reverse64", "single-L64", 64, "native", "reverse", 0., 4.398, 1),
    ]
    for pool, definitions, seed in (("test", test, 64004), ("challenge", challenge, 94623)):
        folder = REFERENCE / "cases" if pool == "test" else ROOT / "private" / "challenge_pool"
        folder.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(seed)
        records = []
        for name, model, size, profile, operation, instant, coupling, batch in definitions:
            phi = rng.normal(size=(batch, size, size))
            if operation == "reverse":
                phi *= .38
                phi += .18 * np.sin(np.arange(size)[None, :, None] * (2 * np.pi / size))
            if name == "coupling_transition":
                phi[1] = phi[0]
            if name == "odd_transfer33":
                phi[:] = 0.
                phi[0, 1, 3] = 1.3
                phi[1] = np.roll(np.rot90(phi[0]), (4, -2), axis=(0, 1))
            logp = -.5 * np.sum(phi * phi, axis=(1, 2)) - .5 * size * size * np.log(2 * np.pi)
            logp += np.linspace(.17, -.23, batch)
            if operation == "reverse":
                logp = np.linspace(-2.3, 1.7, batch)
            request = dict(model=np.array(model), profile=np.array(profile), operation=np.array(operation),
                           phi=phi, logp=logp, t=np.array(instant), lam=np.array(coupling, dtype=np.float64))
            np.savez(folder / (name + ".input.npz"), **request)
            records.append({"id": name, "model": model, "size": size, "profile": profile, "operation": operation,
                            "input": name + ".input.npz", "expected": name + ".expected.npz"})
        (folder / "manifest.json").write_text(json.dumps({"pool": pool, "cases": records}, indent=2) + "\n")
    shutil.copyfile(REFERENCE / "cases" / "native32.input.npz", PUBLIC / "examples" / "probe32.npz")


def references(pools):
    for pool in pools:
        folder = REFERENCE / "cases" if pool == "test" else ROOT / "private" / "challenge_pool"
        manifest = json.loads((folder / "manifest.json").read_text())
        for record in manifest["cases"]:
            metrics = folder / (record["id"] + ".timing.json")
            command = ["taskset", "-c", "40-43", str(PYTHON), str(REFERENCE / "author.py"),
                       str(folder / record["input"]), str(folder / record["expected"]), "--metrics", str(metrics)]
            started = time.perf_counter()
            subprocess.run(command, check=True, env=environment(), timeout=900)
            record["reference_seconds"] = time.perf_counter() - started
            record["reference_metrics"] = json.loads(metrics.read_text())
            record["input_sha256"] = digest(folder / record["input"])
            record["expected_sha256"] = digest(folder / record["expected"])
            print(pool, record["id"], round(record["reference_seconds"], 3), flush=True)
            (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("assets", "references", "all"), default="all")
    parser.add_argument("--pool", choices=("test", "challenge", "all"), default="all")
    args = parser.parse_args()
    os.sched_setaffinity(0, {40, 41, 42, 43})
    os.environ.update(environment())
    if args.stage in ("assets", "all"):
        assets()
        cases()
    if args.stage in ("references", "all"):
        references(("test", "challenge") if args.pool == "all" else (args.pool,))


if __name__ == "__main__":
    main()
