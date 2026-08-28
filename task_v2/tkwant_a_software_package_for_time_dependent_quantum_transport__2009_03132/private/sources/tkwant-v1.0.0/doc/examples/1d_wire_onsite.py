import numpy as np
import matplotlib.pyplot as plt

import kwant
import tkwant


def v(time, tau=8):
    """Time dependent perturbation V(t)"""
    if time < tau:
        return time / tau
    return 1


def create_system(length):

    def onsite_potential(site, time):
        """Time dependent onsite potential (static part + V(t))"""
        return 1 + v(time)

    # system building
    lat = kwant.lattice.square(a=1, norbs=1)
    syst = kwant.Builder()

    # central scattering region
    syst[(lat(x, 0) for x in range(length))] = 1
    syst[lat.neighbors()] = -1
    # time dependent onsite-potential at the leftmost site
    syst[lat(0, 0)] = onsite_potential

    # add leads
    sym = kwant.TranslationalSymmetry((-1, 0))
    lead_left = kwant.Builder(sym)
    lead_left[lat(0, 0)] = 1
    lead_left[lat.neighbors()] = -1
    syst.attach_lead(lead_left)
    syst.attach_lead(lead_left.reversed())

    return syst


def main():

    # parameters
    tmax = 20
    length = 5

    # create system
    syst = create_system(length).finalized()

    # plot the system and dispersion
    chemical_potential = 0
    kwant.plot(syst)
    kwant.plotter.bands(syst.leads[0], show=False)
    plt.plot([-np.pi, np.pi], [chemical_potential, chemical_potential], 'k--')
    plt.show()

    # plot the time-dependent perturbation
    times = np.linspace(0, tmax)
    plt.plot(times, [v(t) for t in times])
    plt.xlabel(r'time $t$')
    plt.ylabel(r'time-dependent perturbation $V(t)$')
    plt.show()

    # define an observable
    density_operator = kwant.operator.Density(syst)

    # do the actual tkwant simulation
    state = tkwant.manybody.State(syst, tmax=tmax)

    densities = []
    for time in times:
        state.evolve(time)
        density = state.evaluate(density_operator)
        densities.append(density)

    # plot the result
    densities = np.array(densities).T
    for site, density in enumerate(densities):
        plt.plot(times, density, label='site {}'.format(site))
    plt.xlabel(r'time $t$')
    plt.ylabel(r'charge density $n$')
    plt.legend()
    plt.show()

if __name__ == '__main__':
    main()
