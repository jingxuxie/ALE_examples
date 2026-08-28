import gzip
import hashlib
import itertools
import json
import pickle
import shutil
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TASKROOT = ROOT.parents[1]
SOURCE = TASKROOT / "source" / "zigzag-majoranas"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    workspace = ROOT / "participant" / "workspace"
    revision = subprocess.check_output(
        ["git", "show", "e3a750a^:zigzag.py"], cwd=SOURCE, text=True
    )
    (workspace / "clean_geometry.py").write_text(revision)
    shutil.copy2(SOURCE / "LICENSE.txt", workspace / "UPSTREAM_LICENSE.txt")
    vendor = workspace / "vendor"
    vendor.mkdir(exist_ok=True)
    runtime = TASKROOT / "source" / "runtime"
    for path in runtime.iterdir():
        if path.name.startswith(("kwant", "tinyarray")):
            target = vendor / path.name
            if path.is_dir():
                shutil.copytree(path, target, dirs_exist_ok=True)
            else:
                shutil.copy2(path, target)
    with gzip.open(SOURCE / "data" / "mfp-vs-gap.pickle", "rb") as stream:
        archive = pickle.load(stream)
    mfps = np.geomspace(10, 5000, 100)
    combos = list(itertools.product(range(100), range(41), [0, 100], [0, 0.1, 0.5, 1, 2, 3], [0, np.pi]))
    assert len(combos) == len(archive) == 98400
    indices = {combo: index for index, combo in enumerate(combos)}
    selections = [
        ("scattering", 25, 3, 0, 0, 0),
        ("scattering", 30, 7, 100, 0.5, 0),
        ("phase_biased", 55, 11, 0, 1, np.pi),
        ("phase_biased", 62, 13, 100, 1, np.pi),
        ("clean_like", 89, 17, 0, 0.5, np.pi),
        ("clean_like", 95, 19, 100, 0.5, np.pi),
    ]
    pool = []
    for family, mfp_index, salt, amplitude, field_T, phase in selections:
        for shift in [0, 1, 2]:
            combo = (mfp_index + shift, salt + shift, amplitude, field_T, phase)
            index = indices[combo]
            case_id = hashlib.sha256(f"disorder-case-{index}".encode()).hexdigest()[:12]
            case = dict(id=case_id, mfp_nm=float(mfps[combo[0]]), salt=int(combo[1]),
                        amplitude_nm=amplitude, field_T=field_T, phase_rad=float(phase))
            pool.append(dict(case=case, family=family, split=["pilot", "discovery", "heldout"][shift],
                             archive_index=index, gap_meV=float(archive[index])))
    write_json(ROOT / "private" / "challenge_pool" / "cases.json", pool)
    sample = dict(id="public-smoke", mfp_nm=float(mfps[99]), salt=0,
                  amplitude_nm=0, field_T=0, phase_rad=0)
    write_json(ROOT / "participant" / "input" / "request.json", {"cases": [sample]})
    write_json(ROOT / "private" / "reference" / "provenance.json", {
        "upstream_head": "012e1ad347959690b7d25597ef8f1af34c43ac8d",
        "visible_revision": "e3a750a^", "private_revision": "e3a750a and later",
        "archive_sha256": hashlib.sha256((SOURCE / "data" / "mfp-vs-gap.pickle").read_bytes()).hexdigest(),
        "archive_evaluations": len(archive), "archive_salts": list(range(41)),
        "paper_says_realizations": 40, "archive_uses_realizations": 41,
        "mapping": "itertools.product(mfp,salt,z_y,B_x,phase); source notebook cell64 named_product preserves keyword order",
        "caveat": "Stored spectral values use the original 31-point search plus local refinement; numerical spot checks required."
    })
    (ROOT / "attempt").mkdir(exist_ok=True)
    print(json.dumps({"cases":len(pool), "archive":len(archive), "root":str(ROOT)}))


if __name__ == "__main__":
    main()
