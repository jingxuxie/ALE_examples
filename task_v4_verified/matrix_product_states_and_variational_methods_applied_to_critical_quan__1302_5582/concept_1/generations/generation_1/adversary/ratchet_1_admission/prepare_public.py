import hashlib
import json
import math
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def patch_text(path, content):
    relative = path.relative_to(Path.cwd().resolve())
    if path.exists() and path.read_text() == content:
        return ""
    if path.exists():
        before = "\n".join("-" + line for line in path.read_text().splitlines())
        after = "\n".join("+" + line for line in content.splitlines())
        return f"*** Update File: {relative}\n@@\n{before}\n{after}\n"
    return f"*** Add File: {relative}\n" + "\n".join("+" + line for line in content.splitlines()) + "\n"


def example(identity, length, dimension, cap, sector, quartic, mass, frequency, seed):
    return {"version": 1, "case_id": identity, "seed": seed,
            "n_sites": length, "local_dim": dimension, "bond_cap": cap,
            "sector": sector, "omega": [frequency] * length,
            "mass2": [mass] * length, "lambda4": [quartic] * length,
            "field": [0.0] * length, "coupling": [1.0] * (length - 1),
            "budget_seconds": 6.0, "wall_seconds": 30.0}


def main():
    patch_parts = []
    production_hashes = {}
    champion = ROOT / "champions/generation_1/submission"
    for name in ("solve.py", "optimizer.py", "contractor.py", "mps.py"):
        source = champion / name
        production_hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        for destination in ("baseline", "workspace"):
            patch_parts.append(patch_text(ROOT / "participant" / destination / name, source.read_text()))
    symmetric = example("public-weak-zero-field", 40, 12, 16, "any", 0.12, -0.046, 0.9, 2041)
    odd = example("public-weak-odd", 48, 12, 20, "odd", 0.08, -0.035, 1.2, 2042)
    odd["coupling"] = [1.1] * 47
    nonuniform = example("public-weak-profile", 40, 14, 16, "any", 0.16, -0.055, 0.8, 2043)
    nonuniform["lambda4"] = [0.16 + 0.03 * math.sin(site) for site in range(40)]
    nonuniform["mass2"] = [-0.055 + 0.01 * math.cos(2 * math.pi * site / 39) for site in range(40)]
    nonuniform["omega"] = [0.8 + 0.3 * (site % 2) for site in range(40)]
    nonuniform["field"] = [0.00015 * math.cos(math.pi * site / 39) for site in range(40)]
    nonuniform["coupling"][19] = 0.3
    for name, request in (("symmetric", symmetric), ("odd", odd), ("nonuniform", nonuniform)):
        path = ROOT / "participant/input" / ("example_" + name + ".json")
        patch_parts.append(patch_text(path, json.dumps(request, indent=2) + "\n"))
    if any(patch_parts):
        patch = "*** Begin Patch\n" + "".join(patch_parts) + "*** End Patch\n"
        subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    scoring = json.loads((ROOT / "participant/input/scoring.json").read_text())
    manifest = {"generation": 1, "production_source": "champions/generation_1/submission",
                "production_sha256": production_hashes, "private_development_artifacts_released": False,
                "target_predeclared": scoring["target"], "stages": scoring["stages"],
                "fresh_attempts_for_this_generation_launched": 0}
    (Path(__file__).parent / "public_preparation.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
