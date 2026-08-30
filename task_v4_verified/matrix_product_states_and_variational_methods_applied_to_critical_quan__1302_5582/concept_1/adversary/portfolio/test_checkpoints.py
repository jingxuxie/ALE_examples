"""Validate the v2 import-free fallback and early wall-deadline behavior."""

import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "v2"))
import contractor
import solve


def request_for(sector):
    return {"version": 1, "case_id": "checkpoint-unit", "seed": 11, "n_sites": 4,
            "local_dim": 6, "bond_cap": 6, "sector": sector, "omega": [0.7, 1.2, 0.9, 1.1],
            "mass2": [-2.0, 0.2, -1.1, -0.4], "lambda4": [1.7, 2.0, 1.8, 2.2],
            "field": [0.0] * 4, "coupling": [0.8, 0.4, 1.2],
            "budget_seconds": 6.0, "wall_seconds": 30.0}


class CheckpointTests(unittest.TestCase):
    def test_basis_state_is_valid_in_every_sector(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "state.npz"
            for sector in ("any", "even", "odd"):
                with self.subTest(sector=sector):
                    request = request_for(sector)
                    solve.write_basis(path, request)
                    measured = contractor.measure(contractor.load_mps(path, request), request)
                    self.assertEqual(measured["max_bond"], 1)
                    if sector != "any":
                        self.assertAlmostEqual(measured["parity"], 1 if sector == "even" else -1)

    def test_expired_wall_budget_keeps_valid_checkpoint(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            folder = Path(temporary)
            request = request_for("odd")
            request["wall_seconds"] = 0.01
            request_path = folder / "request.json"
            request_path.write_text(json.dumps(request))
            output = folder / "state.npz"
            result = subprocess.run([sys.executable, str(ROOT / "v2/solve.py"), "--request", str(request_path),
                                     "--output", str(output)], stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"wall_guard_fired": true', result.stdout)
            self.assertAlmostEqual(contractor.measure(contractor.load_mps(output, request), request)["parity"], -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
