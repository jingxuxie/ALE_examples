import atexit
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

import numpy as np
import scipy.sparse.linalg as sparse_linalg


def ensure_runtime(parent):
    if 'kwant' in sys.modules:
        return
    vendor = Path(__file__).resolve().parent / 'vendor'
    manifest = json.loads((vendor / 'MANIFEST.json').read_text())
    payload = base64.b64decode((vendor / 'runtime.tar.gz.b64').read_bytes())
    if hashlib.sha256(payload).hexdigest() != manifest['archive_sha256']:
        raise RuntimeError('Vendored runtime checksum mismatch')
    cache = tempfile.TemporaryDirectory(prefix='.revision-runtime-', dir=parent)
    atexit.register(cache.cleanup)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not member.isfile():
                raise RuntimeError('Unsafe runtime archive member')
        archive.extractall(cache.name)
    sys.path.insert(0, cache.name)


def sparse_eigsh(matrix, k, sigma, **kwargs):
    if matrix.shape[0] <= k + 1:
        energies, states = np.linalg.eigh(matrix.toarray())
        selected = np.argsort(np.abs(energies - sigma))[:k]
        return energies[selected], states[:, selected]
    indices = np.arange(matrix.shape[0], dtype=float)
    initial = np.cos(0.47 * indices) + 1j * np.sin(0.61 * indices)
    return sparse_linalg.eigsh(
        matrix, k=k, sigma=sigma, v0=initial, tol=1e-10,
        maxiter=10000, **kwargs
    )


def load_source(path, runtime_parent):
    ensure_runtime(runtime_parent)
    import kwant.continuum.discretizer as discretizer

    if not getattr(discretizer._NumericPrinter, '_revision_compat', False):
        class CompatiblePrinter(discretizer._NumericPrinter):
            _revision_compat = True

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.known_functions.update({'sin': 'sin', 'cos': 'cos', 'exp': 'exp'})

        discretizer._NumericPrinter = CompatiblePrinter
    name = 'revision_' + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    discretize = module.discretize

    def compatible_discretize(expression, coords, grid_spacing):
        return discretize(expression, coords=coords, grid=grid_spacing)

    module.discretize = compatible_discretize
    module.mumps_eigsh = sparse_eigsh
    return module
