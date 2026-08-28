import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
sys.dont_write_bytecode = True

import numpy as np
import scipy.constants as constants


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))


def strength(mfp_nm):
    energy_unit = constants.eV * 1e-3
    mass = 0.023 * constants.m_e
    fermi_velocity = np.sqrt(2 * 10 * energy_unit / mass)
    site_dos = (10e-9)**2 * mass / (np.pi * constants.hbar**2)
    variance = constants.hbar * fermi_velocity / (2*np.pi*mfp_nm*1e-9*site_dos)
    return float(np.sqrt(3*variance)/energy_unit)


def prepare(case):
    import clean_model
    from random_field import field

    amplitude = strength(case["mfp_nm"])
    original = clean_model.clean_geometry.get_template_strings

    def templates(*args, **kwargs):
        return {name: text.replace("mu +", "(mu - V_disorder(x, y)) +")
                for name, text in original(*args, **kwargs).items()}

    clean_model.clean_geometry.get_template_strings = templates
    clean_model.clean_geometry.system.cache_clear()
    try:
        system = clean_model.make_system(case["amplitude_nm"])
    finally:
        clean_model.clean_geometry.get_template_strings = original
    params = clean_model.parameters(case["field_T"], case["phase_rad"])
    params["V_disorder"] = field(amplitude, int(case["salt"]))
    return system, params, amplitude


def phase_solver(system, params, ordering='MMD_AT_PLUS_A', emit=None, pivot_threshold=0.0):
    from scipy.sparse.linalg import LinearOperator, eigsh, splu

    def record(event):
        if emit is not None:
            emit(event)

    cache_started = time.perf_counter()
    base = system.hamiltonian_submatrix(params=dict(params, k_x=0.0), sparse=True).tocsc()
    at_pi = system.hamiltonian_submatrix(params=dict(params, k_x=np.pi), sparse=True).tocsc()
    at_half_pi = system.hamiltonian_submatrix(params=dict(params, k_x=np.pi/2), sparse=True).tocsc()
    cosine = (base-at_pi)*0.5
    sine = at_half_pi-base+cosine
    check_phase = 0.713
    check = system.hamiltonian_submatrix(params=dict(params, k_x=check_phase), sparse=True).tocsc()
    difference = check-(base+(np.cos(check_phase)-1)*cosine+np.sin(check_phase)*sine)
    cache_error = float(max(abs(difference.data), default=0))
    if cache_error > 1e-11:
        raise RuntimeError('Source phase dependence is not a single Bloch harmonic')
    record(dict(event='matrix_phase_cache', dimension=base.shape[0],
                independent_phase=check_phase, max_error=cache_error,
                seconds=time.perf_counter()-cache_started))
    del at_pi, at_half_pi, check, difference
    initial_noise = np.random.default_rng(20260827).normal(size=base.shape[0])
    initial = initial_noise.copy()
    computed = {}

    def gap(phase):
        nonlocal initial
        phase = float(np.asarray(phase).reshape(-1)[0])
        if phase in computed:
            record(dict(event='phase_cache_hit', phase=phase))
            return computed[phase]
        started = time.perf_counter()
        matrix = (base+(np.cos(phase)-1)*cosine+np.sin(phase)*sine).tocsc()
        assembled = time.perf_counter()
        record(dict(event='assembled', phase=phase, dimension=matrix.shape[0], nnz=matrix.nnz,
                    seconds=assembled-started))
        factor = splu(matrix, permc_spec=ordering, diag_pivot_thresh=pivot_threshold,
                      options={'SymmetricMode': pivot_threshold == 0})
        factored = time.perf_counter()
        record(dict(event='factored', phase=phase, ordering=ordering,
                    pivot_threshold=pivot_threshold, factor_nnz=int(factor.nnz),
                    seconds=factored-assembled))
        inverse = LinearOperator(matrix.shape, matvec=factor.solve, dtype=matrix.dtype)
        values, vectors = eigsh(matrix, k=4, sigma=0, OPinv=inverse, v0=initial,
                               return_eigenvectors=True, tol=1e-8)
        finished = time.perf_counter()
        residuals = np.linalg.norm(matrix @ vectors - vectors * values, axis=0)
        if float(np.max(residuals)) > 1e-7:
            raise RuntimeError('Unacceptable eigenpair residual from symmetric factorization')
        initial = vectors.sum(axis=1) + 1e-4*initial_noise/np.linalg.norm(initial_noise)
        computed[phase] = float(np.min(np.abs(values)))
        record(dict(event='phase_complete', phase=phase, dimension=matrix.shape[0],
                    eigenvalues=values.tolist(), residuals=residuals.tolist(),
                    minimum_abs_meV=float(np.min(np.abs(values))),
                    assembly_seconds=assembled-started, factor_seconds=factored-assembled,
                    eigensolve_seconds=finished-factored, total_seconds=finished-started))
        return float(np.min(np.abs(values)))

    return gap


def solve(case, ordering='MMD_AT_PLUS_A', emit=None, pivot_threshold=0.0,
          grid_points=31, refinement='fmin'):
    from scipy.optimize import brute, minimize_scalar

    started = time.perf_counter()
    system, params, amplitude = prepare(case)
    if emit is not None:
        emit(dict(event='prepared', id=case['id'], sites=len(system.sites),
                  dimension=4*len(system.sites), strength_meV=amplitude,
                  seconds=time.perf_counter()-started))
    gap = phase_solver(system, params, ordering, emit, pivot_threshold)
    if refinement == 'fmin':
        search = brute(gap, ranges=((0, np.pi),), Ns=grid_points, full_output=True)
        minimum = float(search[1])
        minimizing_phase = float(np.asarray(search[0]).reshape(-1)[0])
    else:
        momenta = np.linspace(0, np.pi, grid_points)
        values = [gap(momentum) for momentum in momenta]
        minima = [(values[0], 0.0), (values[-1], float(np.pi))]
        for index in range(1, grid_points-1):
            if values[index] <= min(values[index-1], values[index+1]):
                refined = minimize_scalar(gap, bounds=(momenta[index-1], momenta[index+1]),
                                          method='bounded', options={'xatol': 1e-5})
                if not refined.success:
                    raise RuntimeError('Bounded phase refinement did not converge')
                minima.append((float(refined.fun), float(refined.x)))
        minimum, minimizing_phase = min(minima)
    if emit is not None:
        emit(dict(event='search_complete', id=case['id'], minimum_meV=float(minimum),
                  minimizing_phase=minimizing_phase, grid_points=grid_points,
                  local_refinement=refinement,
                  runtime_seconds=time.perf_counter()-started))
    return dict(id=case["id"], strength_meV=amplitude, gap_meV=float(minimum))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stored", action="store_true")
    parser.add_argument('--ordering', default='MMD_AT_PLUS_A', choices=['MMD_AT_PLUS_A', 'COLAMD', 'MMD_ATA', 'NATURAL'])
    parser.add_argument('--trace')
    parser.add_argument('--witness-phase', type=float)
    parser.add_argument('--pivot-threshold', type=float, default=0.0)
    parser.add_argument('--memory-gib', type=float, default=12)
    parser.add_argument('--grid-points', type=int, default=31)
    parser.add_argument('--refinement', choices=['fmin', 'bounded'], default='fmin')
    args = parser.parse_args()
    if args.grid_points < 3:
        parser.error('--grid-points must be at least 3')
    if args.trace:
        Path(args.trace).write_text('')
    memory_limit = int(args.memory_gib*1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    cases = json.loads(Path(args.input).read_text())["cases"]
    started = time.perf_counter()

    def emit(event):
        event['elapsed_seconds'] = time.perf_counter()-started
        event['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
        text = json.dumps(event, allow_nan=False)
        print(text, flush=True)
        if args.trace:
            with Path(args.trace).open('a') as stream:
                stream.write(text+'\n')

    if args.stored:
        print('OFFLINE AUTHOR ARCHIVE LOOKUP: not numerical runtime validation.', file=sys.stderr)
        pool = json.loads((ROOT / "private/challenge_pool/cases.json").read_text())
        lookup = {entry["case"]["id"]: entry for entry in pool}
        results = [dict(id=case["id"], strength_meV=strength(case["mfp_nm"]),
                        gap_meV=lookup[case["id"]]["gap_meV"]) for case in cases]
    elif args.witness_phase is not None:
        results = []
        for case in cases:
            prepare_started = time.perf_counter()
            system, params, amplitude = prepare(case)
            emit(dict(event='prepared', id=case['id'], sites=len(system.sites),
                      dimension=4*len(system.sites), strength_meV=amplitude,
                      seconds=time.perf_counter()-prepare_started))
            value = phase_solver(system, params, args.ordering, emit, args.pivot_threshold)(args.witness_phase)
            results.append(dict(id=case['id'], strength_meV=amplitude,
                                phase=args.witness_phase, phase_minimum_abs_meV=value,
                                is_global_gap=False))
    else:
        results = [solve(case, args.ordering, emit, args.pivot_threshold,
                         args.grid_points, args.refinement) for case in cases]
    mode = 'offline_author_archive_lookup' if args.stored else ('single_phase_witness' if args.witness_phase is not None else f'grid_{args.grid_points}_and_{args.refinement}')
    Path(args.output).write_text(json.dumps({"results":results, 'computation':mode,
                                           'runtime_seconds':time.perf_counter()-started}, allow_nan=False))


if __name__ == "__main__":
    main()
