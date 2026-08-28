import math
import os
import numpy as np
from pyblock2.driver.core import DMRGDriver, SymmetryTypes
from assemble import integrals
from measure import make_probes


def simulate(case, settings, scratch):
    driver = DMRGDriver(scratch=str(scratch), symm_type=SymmetryTypes.SZ | SymmetryTypes.CPX,
                        n_threads=2, stack_mem=512 << 20)
    electrons = case['sector']['value'] if case['sector']['kind'] != 'parity' else case['n_sites']
    driver.initialize_system(n_sites=case['n_sites'], n_elec=electrons, spin=case['sector'].get('twosz', 0))
    one_body, two_body = integrals(case, 'before')
    initial = driver.get_qc_mpo(one_body, two_body, iprint=0)
    state = driver.get_random_mps(tag='GS', bond_dim=settings['bond'], nroots=1)
    initial_energy = driver.dmrg(initial, state, n_sweeps=settings['sweeps'], bond_dims=[settings['bond']],
                                 noises=[1e-5] * 2 + [0], thrds=[1e-9], iprint=0)
    one_body, two_body = integrals(case, 'after')
    final = driver.get_qc_mpo(one_body, two_body, iprint=0)
    probes = make_probes(driver, case)
    probes['energy'] = final
    identity = driver.get_identity_mpo()
    rows = []
    previous = 0
    for instant in case['times']:
        if instant > previous:
            count = math.ceil((instant - previous) / settings['step'] - 1e-10)
            delta = (instant - previous) / count if os.environ.get('LEGACY_REPAIR_CLOCK') else instant - previous
            state = driver.td_dmrg(final, state, 1j * delta, n_steps=count, te_type='ts',
                                   n_sub_sweeps=1, normalize_mps=False, final_mps_tag='TD',
                                   bond_dims=[settings['bond']], iprint=0)
        norm = driver.expectation(state, identity, state)
        row = {'time': instant, 'norm': norm.real, 'phonon': 0.0, 'source': 0.0}
        for name, operator in probes.items():
            row[name] = float(np.real(driver.expectation(state, operator, state) / norm))
        rows.append(row)
        previous = instant
    driver.finalize()
    return float(np.real(initial_energy)), rows
