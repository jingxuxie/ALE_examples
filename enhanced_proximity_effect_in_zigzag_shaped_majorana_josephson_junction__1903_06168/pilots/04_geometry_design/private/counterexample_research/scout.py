"""Inventory and measure existing author designs; never select a new gate."""

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import zipfile

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
PILOT = ROOT.parents[1]
sys.path.insert(0, str(PILOT / "private" / "reference"))
import physics
from prepare_reference import RestrictedUnpickler
import numpy as np


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Scout writes must stay in counterexample_research/")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def cells(notebook):
    return [(index, "".join(cell["source"])) for index, cell in enumerate(notebook["cells"]) if cell["cell_type"] == "code"]


def prepare():
    archive_path = PILOT.parents[1] / "source" / "greedy-geometry" / "code.zip"
    archive_bytes = archive_path.read_bytes()
    assert hashlib.md5(archive_bytes).hexdigest() == "750859a1c2c847acdff9eda0ed24873e"
    request = load(PILOT / "private" / "challenge_pool" / "matched_1300" / "request.json")
    save(ROOT / "request.json", request)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        plot_bytes = archive.read("code/generate_plots.ipynb")
        generation_bytes = archive.read("code/generate_data.ipynb")
        plot_cells = cells(json.loads(plot_bytes))
        generation_cells = cells(json.loads(generation_bytes))
        plot_index, plot_source = next((index, source) for index, source in plot_cells if "opt_mu = np.linspace" in source)
        axes = {}
        for node in ast.walk(ast.parse(plot_source)):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ("opt_mu", "opt_EZ"):
                        axes[target.id] = np.linspace(*[ast.literal_eval(argument) for argument in node.value.args]).tolist()
        generation_index, generation_source = next((index, source) for index, source in generation_cells if "def batch_gaps" in source)
        assert "for mu, E_Z in it.product(mu_pts, EZ_pts)" in generation_source
        grid = [{"flat_index": 4 * mu_index + zeeman_index, "mu_normal_mev": mu, "zeeman_mev": zeeman, "mu_index": mu_index, "zeeman_index": zeeman_index} for mu_index, mu in enumerate(axes["opt_mu"]) for zeeman_index, zeeman in enumerate(axes["opt_EZ"])]
        assert len(grid) == 16
        mapping = {"plot_notebook_sha256": hashlib.sha256(plot_bytes).hexdigest(), "generation_notebook_sha256": hashlib.sha256(generation_bytes).hexdigest(), "plot_code_cell_index": plot_index, "batch_gaps_code_cell_index": generation_index, "plot_axis_expressions": {"mu": "np.linspace(10, 15, 4)", "EZ": "np.linspace(0.5, 1.5, 4)"}, "flat_order": "mu outer, EZ inner; index = 4*mu_index + zeeman_index", "units": "meV; plotted normalization Delta_0 equals 1 meV in the supplied Hamiltonian", "grid": grid, "not_the_phase_diagram_grid": "The separate phase-diagram arrays use a 30x30 grid; plotting axis helper arrays of length 10 must not be mistaken for this 4x4 optimization grid."}
        save(ROOT / "official_grid.json", mapping)
        selected = [0, 4, 8, 12, 1, 13]
        save(ROOT / "probe_points.json", [grid[index] for index in selected])
        manifest = {"archive_url": "https://zenodo.org/records/7266609", "archive_version": "v2, created 2022-10-31", "archive_md5": hashlib.md5(archive_bytes).hexdigest(), "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(), "forward_model_sha256": hashlib.sha256((PILOT / "private" / "reference" / "physics.py").read_bytes()).hexdigest(), "designs": [], "excluded": [], "submitted_geometry_comparison": "pending; no counterexample or profile-family dominance claim", "initial_gate_modified": False}
        for name, filename in (("existing_reference", "homogeneous_filtered.p"), ("seed_1", "robustness_checks/seed_1.p"), ("zigzag", "robustness_checks/zigzag.p"), ("no_mirror_sym", "robustness_checks/no_mirror_sym.p")):
            member = "code/data/" + filename
            payload = archive.read(member)
            data = RestrictedUnpickler(io.BytesIO(payload)).load()
            assert len(data["masks_by_epoch"]) == 801
            original = data["masks_by_epoch"][800]
            assert set(original) == {"sc_top", "sc_bot"}
            masks = physics.geometry_arrays(request, {"sc_top": original["sc_top"], "sc_bottom": original["sc_bot"]})
            status = physics.feasibility(request, masks)
            entry = {"name": name, "source_member": member, "source_member_sha256": hashlib.sha256(payload).hexdigest(), "epoch": 800, "snapshots": 801, "shape": list(masks["sc_top"].shape), "dimension": 4 * masks["sc_top"].size, "geometry_sha256": physics.geometry_digest(masks), "manufacturing": status, "stored_16_grid_gaps_mev": np.asarray(data["gaps"]).ravel().tolist() if "gaps" in data else None}
            if name == "no_mirror_sym":
                entry["exclusion"] = "Excluded; no relaxation of mirror, connectivity, or other fabrication constraints. No measurement or mask use in the pool."
                manifest["excluded"].append(entry)
                continue
            if not status["valid"]:
                entry["exclusion"] = "Source mask fails unchanged manufacturing rules; not used or repaired."
                manifest["excluded"].append(entry)
                continue
            entry["non_graph_columns_top"] = int(np.any(np.diff(masks["sc_top"].astype(np.int8), axis=0) < 0, axis=0).sum())
            entry["non_graph_columns_bottom"] = int(np.any(np.diff(masks["sc_bottom"].astype(np.int8), axis=0) > 0, axis=0).sum())
            entry["modifications"] = "None: JSON only renames sc_bot to sc_bottom. No cropping, translation, reflection, alignment, filtering, or pixel changes."
            path = ROOT / "masks" / f"{name}.json"
            save(path, {"schema_version": 1, "request_id": request["request_id"], "geometry": physics.geometry_json(masks)})
            np.savez_compressed(ROOT / "masks" / f"{name}_raw_epoch800.npz", **original)
            roundtrip = load(path)["geometry"]
            assert np.array_equal(np.asarray(roundtrip["sc_top"]), original["sc_top"])
            assert np.array_equal(np.asarray(roundtrip["sc_bottom"]), original["sc_bot"])
            if name == "existing_reference":
                existing = physics.load_result(request, PILOT / "private" / "reference" / "matched_1300.json")
                assert physics.geometry_digest(existing) == physics.geometry_digest(masks)
            manifest["designs"].append(entry)
        save(ROOT / "manifest.json", manifest)
    return manifest


def worker(arguments):
    os.sched_setaffinity(0, {arguments.cpu})
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (540, 541))
    from threadpoolctl import threadpool_info, threadpool_limits
    request = load(ROOT / "request.json")
    points = load(ROOT / "official_grid.json")["grid"] if arguments.full_grid else load(ROOT / "probe_points.json")
    point = next(point for point in points if point["flat_index"] == arguments.point)
    masks = physics.geometry_arrays(request, load(arguments.geometry)["geometry"])
    started = time.monotonic()
    record = {"name": arguments.name, "point": point, "status": "starting", "geometry_sha256": physics.geometry_digest(masks), "manufacturing": physics.feasibility(request, masks), "affinity": sorted(os.sched_getaffinity(0)), "threadpools": threadpool_info(), "momenta_rad": [], "gaps_mev": []}
    save(arguments.output, record)
    try:
        if not record["manufacturing"]["valid"]:
            raise ValueError("Geometry is infeasible; constraints are not relaxed")
        with threadpool_limits(limits=1):
            scenario = {"mu_normal_mev": point["mu_normal_mev"], "zeeman_mev": point["zeeman_mev"]}
            model = physics.ForwardModel(request, masks, scenario)
            record.update(dimension=model.dimension, class_d_invariant=model.topological_invariant(), status="sampling")
            for momentum in np.linspace(0, np.pi, 51):
                energies, _ = model.low_energy(float(momentum))
                record["momenta_rad"].append(float(momentum))
                record["gaps_mev"].append(float(np.min(np.abs(energies))))
                if len(record["gaps_mev"]) % 5 == 0:
                    save(arguments.output, record)
        record.update(status="completed", gap_mev=min(record["gaps_mev"]))
        record["physically_valid"] = record["class_d_invariant"] == -1 and record["gap_mev"] > 1e-5
    except Exception as error:
        record.update(status="exception", error=f"{type(error).__name__}: {error}")
    usage = resource.getrusage(resource.RUSAGE_SELF)
    record.update(elapsed_seconds=time.monotonic() - started, cpu_seconds=usage.ru_utime + usage.ru_stime, peak_rss_kib=usage.ru_maxrss)
    save(arguments.output, record)


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)


def summarize(names, comparison=False, full_grid=False):
    mapping = load(ROOT / "official_grid.json")
    points = mapping["grid"] if full_grid else load(ROOT / "probe_points.json")
    manifest = load(ROOT / "manifest.json")
    observations = []
    for name in names:
        for point in points:
            path = ROOT / "measurements" / f"{name}_grid_{point['flat_index']:02d}.json"
            observations.append(load(path) if path.exists() else {"name": name, "point": point, "status": "not_started"})
    complete = [row for row in observations if row.get("status") == "completed"]
    report = {"complete": len(complete) == len(observations), "completed_measurements": len(complete), "expected_measurements": len(observations), "rows": observations, "profile_family_comparison": "pending; reference-only measurements do not establish a counterexample", "ratchet_or_acceptance_change": False}
    if not comparison:
        stored = next(entry["stored_16_grid_gaps_mev"] for entry in manifest["designs"] if entry["name"] == "existing_reference")
        errors = [abs(row["gap_mev"] - stored[row["point"]["flat_index"]]) for row in complete if row["name"] == "existing_reference"]
        report["existing_reference_stored_grid_max_error_mev"] = max(errors) if errors else None
        report["pointwise_author_reference_inventory"] = []
        for point in points:
            eligible = [row for row in complete if row["point"]["flat_index"] == point["flat_index"] and row.get("physically_valid")]
            best = max(eligible, key=lambda row: row["gap_mev"]) if eligible else None
            report["pointwise_author_reference_inventory"].append({"point": point, "best_measured_author_design": None if best is None else best["name"], "best_author_gap_mev": None if best is None else best["gap_mev"], "comparison_with_submitted_geometry": "not performed"})
        output = ROOT / "pool_summary.json"
    else:
        output = ROOT / f"comparison_{names[0]}.json"
    save(output, report)
    if not comparison:
        lines = ["# Existing author-design probe inventory", "", "**No counterexample is claimed.** Main must compare completed submitted geometries on these identical points before any acceptance or ratchet decision.", "", "## Official grid", "", f"`generate_plots.ipynb` code cell {mapping['plot_code_cell_index']} defines mu = linspace(10,15,4), EZ = linspace(0.5,1.5,4). `generate_data.ipynb` code cell {mapping['batch_gaps_code_cell_index']} orders `product(mu_pts, EZ_pts)`: flat index = 4*mu_index + EZ_index. The 16 exact points and notebook hashes are in `official_grid.json`. This is not the separate 30x30 phase-diagram grid.", "", "## Unmodified artifacts", "", "All included masks are exact epoch 800 of 801 snapshots in Zenodo 7266609 v2. Raw NPZ arrays, canonical geometry JSON, per-member hashes, morphology, and unchanged manufacturing checks are saved. The seed and zigzag robustness archives contain no stored 16-point gap arrays; their values below are fresh physical measurements, not claimed archived values. `no_mirror_sym` is excluded and never used as a hard reference.", "", "## Full 51-momentum probes", "", "| Grid index | mu / EZ (meV) | existing_reference | seed_1 | zigzag |", "|---|---|---|---|---|"]
        for point in points:
            values = []
            for name in ("existing_reference", "seed_1", "zigzag"):
                selected = next((row for row in observations if row["name"] == name and row["point"]["flat_index"] == point["flat_index"]), {})
                values.append(f"{selected['gap_mev']:.8f} (Q={selected['class_d_invariant']})" if selected.get("status") == "completed" else selected.get("status", "excluded"))
            lines.append(f"| {point['flat_index']} | {point['mu_normal_mev']:.8g} / {point['zeeman_mev']:.8g} | " + " | ".join(values) + " |")
        lines.extend(["", f"Completed {len(complete)}/{len(observations)} measurements. Existing-reference agreement with the stored official 16-grid values: maximum error {report['existing_reference_stored_grid_max_error_mev']} meV.", "", "Non-topological or incomplete values are not eligible strong references. Pointwise maxima across different author masks are an inventory, not a single realizable robust design. A public-screen score near 0.18 at different operating points cannot substitute for the pending submitted-geometry comparison. The initial participant, evaluator, challenge pool, and attempt are unchanged."])
        (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2), flush=True)


def run(arguments):
    started = time.monotonic()
    allowed = sorted(os.sched_getaffinity(0))
    chosen = allowed[-min(arguments.workers, 12):]
    os.sched_setaffinity(0, chosen)
    comparison = arguments.geometry is not None
    if comparison:
        name = "submitted_" + arguments.geometry.stem
        if arguments.full_grid:
            name += "_official16"
        names = [name]
        geometries = {name: arguments.geometry.resolve()}
        deadline = time.time() + arguments.wall_seconds
    else:
        manifest = prepare()
        names = [entry["name"] for entry in manifest["designs"]]
        geometries = {name: ROOT / "masks" / f"{name}.json" for name in names}
        deadline = load(ROOT / "scout_clock.json")["started_unix_seconds"] + 570
    points = load(ROOT / "official_grid.json")["grid"] if arguments.full_grid else load(ROOT / "probe_points.json")
    pending = [(name, point) for point in points for name in names]
    active = {}
    free = list(chosen)
    save(ROOT / ("comparison_runtime.json" if comparison else "runtime.json"), {"allowed_cpus": allowed, "chosen_cpus": chosen, "workers": len(chosen), "blas_threads": 1, "deadline_unix_seconds": deadline, "source_scout": not comparison})
    try:
        while (pending or active) and time.time() < deadline:
            while pending and free:
                cpu = free.pop(0)
                name, point = pending.pop(0)
                path = ROOT / "measurements" / f"{name}_grid_{point['flat_index']:02d}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--geometry", str(geometries[name]), "--name", name, "--point", str(point["flat_index"]), "--cpu", str(cpu), "--output", str(path)]
                if arguments.full_grid:
                    command.append("--full-grid")
                with path.with_suffix(".stderr.log").open("w") as log:
                    process = subprocess.Popen(command, cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                active[cpu] = (process, path)
                print(f"start {name} grid={point['flat_index']} cpu={cpu}", flush=True)
            for cpu, (process, path) in list(active.items()):
                if process.poll() is not None:
                    value = load(path) if path.exists() else {"status": "worker_failed_before_report"}
                    print(f"finish {path.stem}: {value.get('status')} gap={value.get('gap_mev')} Q={value.get('class_d_invariant')}", flush=True)
                    del active[cpu]
                    free.append(cpu)
            time.sleep(.15)
    finally:
        for process, path in active.values():
            stop(process)
            if path.exists():
                value = load(path)
                value.update(status="scout_timeout", stage_at_timeout=value.get("status"))
                save(path, value)
    summarize(names, comparison, arguments.full_grid)
    print(f"offline_scout_wall_seconds={time.monotonic() - started:.3f}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--geometry", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--point", type=int)
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--wall-seconds", type=float, default=540)
    parser.add_argument("--full-grid", action="store_true")
    arguments = parser.parse_args()
    if arguments.worker:
        worker(arguments)
    else:
        run(arguments)


if __name__ == "__main__":
    main()
