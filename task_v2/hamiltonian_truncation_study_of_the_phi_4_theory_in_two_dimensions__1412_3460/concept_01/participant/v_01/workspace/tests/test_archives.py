import json
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[2]


class ArchiveTests(unittest.TestCase):
    def test_operator_algebra(self):
        request = json.loads((ROOT / 'input' / 'campaign.json').read_text())
        for case in request['cases']:
            folder = ROOT / 'input' / request['archive_root'] / case['archive']
            manifest = json.loads((folder / 'manifest.json').read_text())
            for sector in manifest['sectors']:
                label = sector['name']
                basis = np.load(folder / (label + '_basis.npz'))
                energy = basis['occupations'] @ basis['frequencies']
                self.assertLess(np.max(abs(energy - basis['free_energy'])), 1e-9)
                if sector['momentum'] is not None:
                    self.assertTrue(np.all(basis['occupations'] @ basis['modes'] == sector['momentum']))
                operators = {(item['degree'], item['transfer']): sparse.load_npz(folder / item['file'])
                             for item in manifest['operators'] if item['sector'] == label}
                self.assertLess(np.max(abs(operators[(0, 0)].diagonal() - case['length'])), 1e-12)
                for (degree, transfer), matrix in operators.items():
                    error = matrix - operators[(degree, -transfer)].T
                    self.assertLess(np.max(abs(error.data), initial=0), 1e-10)


if __name__ == '__main__':
    unittest.main()
