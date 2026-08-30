import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from model import baseline, full_hamiltonian, pack, unpack
from evaluate import load_witness
import remote_reference as remote
from test_validation import CONFIG


class RemoteValidation(unittest.TestCase):
    def test_all_channels_independent_and_c4(self):
        generator = np.random.default_rng(73)
        horizontal, vertical = generator.uniform(-np.pi, np.pi, (2, 17))
        rotation = np.diag([1.0, 1j, 1.0, 1j])
        for index in range(30):
            parameters = pack(baseline())
            parameters[index] += 0.117
            witness = unpack(parameters)
            actual = remote.matrix_values(remote.fourier_hoppings(witness), horizontal, vertical)
            expected = full_hamiltonian(witness, horizontal, vertical)
            np.testing.assert_allclose(actual, expected, atol=4e-14)
            np.testing.assert_allclose(full_hamiltonian(witness, -vertical, horizontal), rotation@expected@rotation.conj().T, atol=4e-14)

    def test_gap12_required_even_with_large_gap01(self):
        def synthetic_spectrum(matrices):
            return np.broadcast_to([-100.0, 100.0, 100.0+1e-10, 200.0], matrices.shape[:-1])
        with patch("remote_reference.np.linalg.eigvalsh", side_effect=synthetic_spectrum):
            result = remote.spectral_certificate(baseline(), CONFIG, mesh=17)
        self.assertFalse(result["certified"])
        self.assertGreater(result["preliminary_gap_01"], 0.0)
        self.assertLess(result["preliminary_gap_12"], 0.0)

    def test_hardened_artifact_reader(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"adversary/remote_band_probe") as name:
            directory = Path(name)
            regular = directory/"regular.json"
            regular.write_text("{}")
            symbolic = directory/"symbolic.json"
            symbolic.symlink_to(regular)
            with self.assertRaises(OSError):
                load_witness(symbolic, CONFIG)
            hard = directory/"hard.json"
            os.link(regular, hard)
            with self.assertRaises(ValueError):
                load_witness(hard, CONFIG)
            fifo = directory/"fifo.json"
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                load_witness(fifo, CONFIG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
