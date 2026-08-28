import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import zipfile


HERE = Path(__file__).resolve().parent
RATCHET = HERE.parents[1]
PILOT = RATCHET.parent
ROOT = PILOT.parents[1]
sys.path.insert(0, str(PILOT / "private/reference"))
from prepare_reference import RestrictedUnpickler
import physics


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    baseline_path = PILOT / "private/scale_research/run/results/matched_1940_scale_audit.json"
    baseline_result = json.loads(baseline_path.read_text())
    template = json.loads((PILOT / "private/scale_research/request.json").read_text())
    template["baseline_geometry"] = baseline_result["geometry"]
    source_archive = ROOT / "source/greedy-geometry/code.zip"
    member = "code/data/homogeneous_filtered_1940.p"
    with zipfile.ZipFile(source_archive) as archive:
        payload = archive.read(member)
    data = RestrictedUnpickler(io.BytesIO(payload)).load()
    original = data["masks_by_epoch"][800]
    strong_masks = {"sc_top": original["sc_top"], "sc_bottom": original["sc_bot"]}
    cases = {
        "lower_offset": [(10.2, 0.74), (12.0, 1.08), (14.4, 1.32)],
        "central_offset": [(10.7, 0.78), (12.8, 1.15), (14.8, 1.41)],
        "high_density": [(10.9, 0.70), (13.2, 1.02), (14.9, 1.46)],
    }
    manifest = {
        "source_archive_sha256": hashlib.sha256(source_archive.read_bytes()).hexdigest(),
        "source_member": member,
        "source_member_sha256": hashlib.sha256(payload).hexdigest(),
        "epoch": 800,
        "source_geometry_modifications": "none; only sc_bot key renamed sc_bottom",
        "strong_geometry_sha256": physics.geometry_digest(strong_masks),
        "public_baseline_origin": str(baseline_path.relative_to(ROOT)),
        "public_baseline_file_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "heldout_design": "Three preregistered interior operating triples, distinct from the inspected scale-audit triple. They span the same source-supported parameter region and are visible when each request is delivered. No output labels are public.",
        "cases": {},
    }
    for identifier, pairs in cases.items():
        scenarios = [{"mu_normal_mev": chemical, "zeeman_mev": field} for chemical, field in pairs]
        request = dict(template, request_id=identifier, operating_points=scenarios)
        case = RATCHET / "private/challenge_pool" / identifier
        save(case / "request.json", request)
        save(case / "scenarios.json", scenarios)
        save(HERE / f"{identifier}.json", {"schema_version": 1, "request_id": identifier, "geometry": physics.geometry_json(strong_masks)})
        manifest["cases"][identifier] = {"operating_points": scenarios, "request_sha256": hashlib.sha256((case / "request.json").read_bytes()).hexdigest()}
        if not physics.feasibility(request, strong_masks)["valid"]:
            raise ValueError("Unmodified source geometry is infeasible")
        if not physics.feasibility(request, physics.geometry_arrays(request, request["baseline_geometry"]))["valid"]:
            raise ValueError("Frozen public baseline is infeasible")
    example_points = json.loads((PILOT / "private/scale_research/scenarios.json").read_text())
    save(RATCHET / "participant/input/example.json", dict(template, request_id="example", operating_points=example_points))
    for name in ("physics.py", "forward.py"):
        destination = RATCHET / "participant/workspace" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PILOT / "participant/workspace" / name, destination)
    for name in ("solve.py", "geometry.py", "fast_physics.py"):
        shutil.copyfile(PILOT / "attempt" / name, RATCHET / "participant/workspace/baseline" / name)
    shutil.copyfile(PILOT / "private/evaluator.py", RATCHET / "private/evaluator.py")
    shutil.copyfile(PILOT / "private/reference/physics.py", HERE / "physics.py")
    (RATCHET / "attempt").mkdir(exist_ok=True)
    save(HERE / "source_manifest.json", manifest)
    print(json.dumps({"cases": list(cases), "strong_geometry_sha256": manifest["strong_geometry_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
