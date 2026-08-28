import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import time
import types

sys.dont_write_bytecode = True

import numpy as np

from solve import ROOT, prepare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    started = time.perf_counter()
    taskroot = ROOT.parents[1]
    repository = taskroot / 'source/zigzag-majoranas'
    case = json.loads(arguments.input.read_text())['cases'][0]
    system, params, amplitude = prepare(case)
    import clean_model
    before = subprocess.check_output(['git', '-C', str(repository), 'show', 'e3a750a^:zigzag.py'])
    assert before == (ROOT / 'participant/workspace/clean_geometry.py').read_bytes()
    after = subprocess.check_output(['git', '-C', str(repository), 'show', 'e3a750a:zigzag.py'])
    source = types.ModuleType('source_disorder_revision')
    exec(compile(after, 'e3a750a:zigzag.py', 'exec'), source.__dict__)
    expected_strength = source.disorder_strength_from_mfp(case['mfp_nm'], 10, 10, dim=2)
    source_field = source.disorder_potential(expected_strength, int(case['salt']))
    field_error = max(abs(params['V_disorder'](*site.pos) - source_field(*site.pos)) for site in system.sites)
    source_system = source.system(
        W=200, L_x=3900, L_sc_up=300, L_sc_down=300, z_x=1300,
        z_y=case['amplitude_nm'], a=10, shape='parallel_curve', transverse_soi=True,
        mu_from_bottom_of_spin_orbit_bands=True, k_x_in_sc=True, wraparound=True,
        infinite=True, substitutions=(('mu +', '(mu - V_disorder(x, y)) +'),)
    )
    assert [tuple(site.tag) for site in system.sites] == [tuple(site.tag) for site in source_system.sites]
    phase_records = []
    for phase in (0.0, 0.713, np.pi):
        matrix = system.hamiltonian_submatrix(params=dict(params, k_x=phase), sparse=True).tocsc()
        original = source_system.hamiltonian_submatrix(
            params=dict(params, k_x=phase, V_disorder=source_field), sparse=True
        ).tocsc()
        difference = matrix-original
        hermitian = matrix-matrix.conj().T
        error = float(max(abs(difference.data), default=0))
        hermitian_error = float(max(abs(hermitian.data), default=0))
        assert matrix.shape == (124800, 124800)
        assert error < 1e-11 and hermitian_error < 1e-12
        phase_records.append(dict(phase=float(phase), dimension=matrix.shape[0], nnz=matrix.nnz,
                                  source_matrix_max_error=error, hermiticity_max_error=hermitian_error))
    archive_path = repository / 'data/mfp-vs-gap.pickle'
    with gzip.open(archive_path, 'rb') as stream:
        archive = pickle.load(stream)
    mfps = np.geomspace(10, 5000, 100)
    mfp_index = int(np.argmin(abs(mfps-case['mfp_nm'])))
    assert abs(mfps[mfp_index]-case['mfp_nm']) < 1e-10
    amplitude_index = [0, 100].index(case['amplitude_nm'])
    field_index = [0, 0.1, 0.5, 1, 2, 3].index(case['field_T'])
    phase_index = [0, np.pi].index(case['phase_rad'])
    archive_index = ((((mfp_index*41+case['salt'])*2+amplitude_index)*6+field_index)*2+phase_index)
    assert len(archive) == 98400
    expected_gap = float(archive[archive_index])
    assert abs(expected_gap-0.22934536743383552) < 1e-14
    try:
        import kwant.linalg.mumps
        mumps_available = True
    except ImportError:
        mumps_available = False
    report = dict(status='source_matrix_and_archive_mapping_validated', case=case,
                  source_revision='e3a750a60d667ce393c6917b4301a503aa171648',
                  participant_snapshot_byte_exact=True,
                  strength_meV=amplitude, source_strength_meV=float(expected_strength),
                  strength_absolute_error=float(abs(amplitude-expected_strength)),
                  disorder_field_max_error=float(field_error), phase_checks=phase_records,
                  archive_evaluations=len(archive), archive_index=archive_index,
                  archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                  expected_gap_meV=expected_gap, mumps_available=mumps_available,
                  global_gap_numerically_validated=False, seconds=time.perf_counter()-started)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
