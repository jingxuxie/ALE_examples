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
    champion = ROOT / "champions/generation_2/submission"
    for name in ("solve.py", "fast.py", "optimizer.py", "contractor.py"):
        source = champion / name
        production_hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        for destination in ("baseline", "workspace"):
            patch_parts.append(patch_text(ROOT / "participant" / destination / name, source.read_text()))
    for destination in ("baseline", "workspace"):
        obsolete = ROOT / "participant" / destination / "mps.py"
        if obsolete.exists():
            patch_parts.append(f"*** Delete File: {obsolete.relative_to(Path.cwd().resolve())}\n")
    symmetric = example("public-nonuniform-even", 48, 10, 14, "even", 0.06, -0.031, 0.60, 3041)
    symmetric["coupling"] = [0.9 + 0.1 * math.sin(site / 3.0) for site in range(47)]
    symmetric["coupling"][15] = 0.25
    symmetric["coupling"][31] = 0.35
    odd = example("public-weaklink-odd", 40, 12, 12, "odd", 0.055, -0.027, 0.57, 3042)
    odd["mass2"] = [-0.027 + 0.008 * math.cos(site / 5.0) for site in range(40)]
    odd["coupling"] = [0.9 + 0.1 * math.sin(site / 4.0) for site in range(39)]
    for site in (9, 19, 29):
        odd["coupling"][site] = 0.075
    nonuniform = example("public-varied-profile", 40, 14, 16, "even", 0.08, -0.031, 0.6, 3043)
    nonuniform["lambda4"] = [0.08 + 0.015 * math.sin(site) for site in range(40)]
    nonuniform["mass2"] = [-0.031 + 0.01 * math.cos(2 * math.pi * site / 39) for site in range(40)]
    nonuniform["omega"] = [0.6 + 0.15 * (site % 2) for site in range(40)]
    nonuniform["coupling"][19] = 0.09
    for name, request in (("symmetric", symmetric), ("odd", odd), ("nonuniform", nonuniform)):
        path = ROOT / "participant/input" / ("example_" + name + ".json")
        patch_parts.append(patch_text(path, json.dumps(request, indent=2) + "\n"))
    task = """# Robust variational field states in fixed parity sectors

## Mission
Improve the supplied current-champion optimizer for finite, nonuniform phi4
chains. Return low-energy matrix product states within the requested bond cap
and global parity sector. The hidden suite varies mass and quartic profiles,
weak links, and alternating couplings. This is a finite-Hamiltonian optimizer
task, not a continuum extrapolation or gap-prediction task.

## Assets and interface
`workspace/` contains a starting solver and public energy contractor;
`baseline/` is the frozen champion production code. `input/` contains examples,
the exact Hamiltonian and array contract, and the scoring specification.
Submit a self-contained directory with `solve.py`, implementing
`python solve.py --request REQUEST.json --output STATE.npz`.
Return MPS tensors, not energy claims. Copy read-only starter files into the
writable submission directory before making changes.

## Objective
The checker recomputes energies and rewards logarithmic improvement over a
frozen baseline at two compute budgets, worst-family quality, and runtime.
Pass with score >= 80, core >= 0.80, worst-family >= 0.70, each long-budget
quality >= 0.55, and all outputs valid. Reference energies come from attainable
same-cap states; they are not asserted exact ground energies.
See `input/CONTRACT.md` and `input/scoring.json`.

## Resources
Eight hidden chains, each run independently at 6 and 40 CPU seconds, with
30/120-second solver wall guards. Interpreter startup and imports count;
trusted launcher setup does not. One execution thread, 2 GiB address space,
no GPU, network, subprocesses, or cross-request state. Python, NumPy, and SciPy
are available. The participant tree is read-only; only the submission/output
directory is writable during the fresh attempt.
"""
    patch_parts.append(patch_text(ROOT / "participant/TASK.md", task))
    contract = (ROOT / "generations/generation_1/participant/input/CONTRACT.md").read_text()
    contract = contract.replace("# Contract v2", "# Contract v3")
    contract = contract.replace('`sector` (`"any"`, `"even"`, or `"odd"`)',
                                '`sector` (`"even"` or `"odd"`)')
    contract = contract.replace('`sector != "any"` implies every `field` is zero.',
                                'Every `field` is exactly zero in this generation.')
    contract = contract.replace('and abs(field) <= 0.004.', 'and field = 0.')
    patch_parts.append(patch_text(ROOT / "participant/input/CONTRACT.md", contract))
    readme = """# Current-champion production snapshot

These four Python files are copied byte-for-byte from the passing champion of
the preceding generation. Development logs, experimental states, hidden cases,
and alternative solvers are not included. See `../TASK.md` and the files in
`../input/` for the executable interface, finite Hamiltonian, and fixed targets.
"""
    for directory in ("baseline", "workspace"):
        patch_parts.append(patch_text(ROOT / "participant" / directory / "README.md", readme))
    if any(patch_parts):
        patch = "*** Begin Patch\n" + "".join(patch_parts) + "*** End Patch\n"
        subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    scoring = json.loads((ROOT / "participant/input/scoring.json").read_text())
    manifest = {"generation": 2, "production_source": "champions/generation_2/submission",
                "production_sha256": production_hashes, "private_development_artifacts_released": False,
                "target_predeclared": scoring["target"], "stages": scoring["stages"],
                "fresh_attempts_for_this_generation_launched": 0}
    (Path(__file__).parent / "public_preparation.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
