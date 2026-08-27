import tkwant
from tkwant import leads, manybody
import kwant
import kwantspectrum

import functools
import cmath
import numpy as np
from scipy.special import erf
import matplotlib.pyplot as plt


def am_master():
    """Return true for the MPI master rank"""
    return tkwant.mpi.get_communicator().rank == 0


def make_system(L=400):

    def gaussian(time, t0=40, A=1.57, sigma=24):
        return A * (1 + erf((time - t0) / sigma))

    # time dependent coupling with gaussian pulse
    def coupling_nn(site1, site2, time):
        return - cmath.exp(- 1j * gaussian(time))

    # system building
    lat = kwant.lattice.square(a=1, norbs=1)
    syst = kwant.Builder()

    # central scattering region
    syst[(lat(x, 0) for x in range(L))] = 1
    syst[lat.neighbors()] = -1
    # time dependent coupling between two sites in the center
    syst[lat(L // 2, 0), lat(L // 2 - 1, 0)] = coupling_nn

    # add leads
    sym = kwant.TranslationalSymmetry((-1, 0))
    lead_left = kwant.Builder(sym)
    lead_left[lat(0, 0)] = 1
    lead_left[lat.neighbors()] = -1
    syst.attach_lead(lead_left)
    syst.attach_lead(lead_left.reversed())

    return syst


def main():

    syst = make_system().finalized()
    sites = [site.pos[0] for site in syst.sites]
    times = [40, 80, 120, 160]

    density_operator = kwant.operator.Density(syst)

    # calculate the spectrum E(k) for all leads
    spectra = kwantspectrum.spectra(syst.leads)

    # estimate the cutoff energy Ecut from T, \mu and f(E)
    # All states are effectively empty above E_cut
    occupations = manybody.lead_occupation(chemical_potential=0, temperature=0)
    emin, emax = manybody.calc_energy_cutoffs(occupations)

    # define boundary conditions
    bdr = leads.automatic_boundary(spectra, tmax=max(times), emin=emin, emax=emax)

    # calculate the k intervals for the quadrature
    interval_type = functools.partial(manybody.Interval, order=20,
                                      quadrature='gausslegendre')
    intervals = manybody.calc_intervals(spectra, occupations, interval_type)
    intervals = manybody.split_intervals(intervals, number_subintervals=10)

    # calculate all onebody scattering states at t = 0
    tasks = manybody.calc_tasks(intervals, spectra, occupations)
    psi_init = manybody.calc_initial_state(syst, tasks, bdr)

    # set up the manybody wave function
    wave_function = manybody.WaveFunction(psi_init, tasks)

    density0 = wave_function.evaluate(density_operator)

    for time in times:
        wave_function.evolve(time)
        density = wave_function.evaluate(density_operator)
        if am_master():
            plt.plot(sites, density - density0, label='time={}'.format(time))

    if am_master():
        plt.legend()
        plt.xlabel(r'site position $i$')
        plt.ylabel(r'charge density $n$')
        plt.show()


if __name__ == '__main__':
    main()
