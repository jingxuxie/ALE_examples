import math
from pathlib import Path
import numpy as np
from pyblock2.driver.core import DMRGDriver, SymmetryTypes, MPOAlgorithmTypes
from models import choose_order, hamiltonian_terms, local_operators, observables


class Evolution:
    def __init__(self, case, directory, settings):
        self.case = case
        self.settings = settings
        self.order = choose_order(case)
        self.position = {site: index for index, site in enumerate(self.order)}
        self.driver = DMRGDriver(scratch=str(Path(directory) / 'scratch'), symm_type=SymmetryTypes.SAny | SymmetryTypes.CPX,
                                 stack_mem=768 << 20, n_threads=2)
        sector = case['sector']
        if sector['kind'] == 'parity':
            self.driver.set_symmetry_groups('Z2Fermi')
            quantum = self.driver.bw.SX
            target = quantum(sector['value'])
            vacuum = quantum(0)
            electron_basis = [(quantum(0), 2), (quantum(1), 2)]
        elif sector['kind'] == 'number':
            self.driver.set_symmetry_groups('U1Fermi')
            quantum = self.driver.bw.SX
            target = quantum(sector['value'])
            vacuum = quantum(0)
            electron_basis = [(quantum(0), 1), (quantum(1), 2), (quantum(2), 1)]
        else:
            self.driver.set_symmetry_groups('U1Fermi', 'U1')
            quantum = self.driver.bw.SX
            target = quantum(sector['value'], sector['twosz'])
            vacuum = quantum(0, 0)
            electron_basis = [(quantum(0, 0), 1), (quantum(1, 1), 1), (quantum(1, -1), 1), (quantum(2, 0), 1)]
        self.driver.initialize_system(n_sites=len(self.order), vacuum=vacuum, target=target, hamil_init=False)
        basis, operators = [], []
        for physical in self.order:
            levels = None if physical < case['n_sites'] else case['phonons'][physical - case['n_sites']]['levels']
            basis.append(electron_basis if levels is None else [(vacuum, levels)])
            local = local_operators(levels)
            if levels is None and sector['kind'] == 'parity':
                permutation = [0, 3, 1, 2]
                local = {name: matrix[np.ix_(permutation, permutation)] for name, matrix in local.items()}
            operators.append(local)
        self.driver.ghamil = self.driver.get_custom_hamiltonian(basis, operators)
        self.initial_mpo = self.mpo(hamiltonian_terms(case, 'before'))
        self.final_mpo = self.mpo(hamiltonian_terms(case, 'after'))
        self.identity = self.driver.get_identity_mpo()
        self.probes = {name: self.mpo(terms) if terms else None for name, terms in observables(case).items()}

    def mpo(self, terms):
        builder = self.driver.expr_builder()
        for ops, sites, value in terms:
            if abs(value) > 1e-15:
                builder.add_term(ops, [self.position[site] for site in sites], complex(value))
        return self.driver.get_mpo(builder.finalize(adjust_order=True, fermionic_ops='cdCD'),
                                   algo_type=MPOAlgorithmTypes.FastBipartite, iprint=0)

    def prepare(self):
        import block2
        block2.Random.rand_seed(17)
        bond = self.settings['bond']
        sweeps = self.settings['sweeps']
        self.state = self.driver.get_random_mps(tag='GS', bond_dim=min(32, bond), nroots=1)
        energy = self.driver.dmrg(self.initial_mpo, self.state, n_sweeps=sweeps,
                                  bond_dims=[min(32, bond)] * 2 + [bond] * (sweeps - 2),
                                  noises=[1e-5] * 2 + [1e-7] * 2 + [0],
                                  thrds=[1e-10], tol=1e-10, cutoff=self.settings['cutoff'],
                                  dav_max_iter=200, iprint=0)
        return float(np.real(energy))

    def measure(self, time_value):
        norm = self.driver.expectation(self.state, self.identity, self.state)
        row = {'time': float(time_value), 'norm': float(norm.real)}
        for name, operator in self.probes.items():
            value = 0 if operator is None else self.driver.expectation(self.state, operator, self.state) / norm
            row[name] = float(np.real(value))
        return row

    def advance(self, duration):
        count = max(1, math.ceil(duration / self.settings['step'] - 1e-10))
        self.state = self.driver.td_dmrg(self.final_mpo, self.state, target_t=1j * duration, n_steps=count,
                                         te_type='ts', n_sub_sweeps=1, normalize_mps=False,
                                         final_mps_tag='TD', bond_dims=[self.settings['bond']],
                                         cutoff=self.settings['cutoff'], iprint=0)

    def close(self):
        self.driver.finalize()
