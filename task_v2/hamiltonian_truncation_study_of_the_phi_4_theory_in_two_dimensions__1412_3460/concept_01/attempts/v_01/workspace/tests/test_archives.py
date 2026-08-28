import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy import sparse

REQUEST = os.environ.get('TASK_REQUEST')


class ArchiveTests(unittest.TestCase):
    @unittest.skipUnless(REQUEST, 'Set TASK_REQUEST for the optional supplied-archive integration check')
    def test_operator_algebra(self):
        request_path = Path(REQUEST).resolve()
        request = json.loads(request_path.read_text())
        root = Path(request['archive_root'])
        if not root.is_absolute():
            root = request_path.parent / root
        for case in request['cases']:
            folder = root / case['archive']
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
