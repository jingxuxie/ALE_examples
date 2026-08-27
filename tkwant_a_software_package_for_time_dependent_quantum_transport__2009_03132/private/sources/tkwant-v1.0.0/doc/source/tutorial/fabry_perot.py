from math import sin, pi
import matplotlib.pyplot as plt

import tkwant
import kwant


def am_master():
    """Return true for the MPI master rank"""
    return tkwant.mpi.get_communicator().rank == 0


def make_fabry_perot_system():

    # Define an empty tight-binding system on a square lattice.
    lat = kwant.lattice.square(norbs=1)
    syst = kwant.Builder()

    # Central scattering region.
    syst[(lat(x, 0) for x in range(80))] = 0
    syst[lat.neighbors()] = -1
    # Backgate potential.
    syst[(lat(x, 0) for x in range(5, 75))] = -0.0956
    # Barrier potential.
    syst[[lat(4, 0), lat(75, 0)]] = 5.19615

    # Attach lead on the left- and on the right-hand side.
    sym = kwant.TranslationalSymmetry((-1, 0))
    lead = kwant.Builder(sym)
    lead[(lat(0, 0))] = 0
    lead[lat.neighbors()] = -1
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())

    return syst, lat


# Phase from the time integrated voltage V(t).
def phi(time):
    vb, tau = 0.6, 30.
    if time > tau:
        return vb * (time - tau / 2.)
    return vb / 2. * (time - tau / pi * sin(pi * time / tau))


def main():

    times = range(220)

    # Make the system and add voltage V(t) to the left lead (index 0).
    syst, lat = make_fabry_perot_system()
    tkwant.leads.add_voltage(syst, 0, phi)
    syst = syst.finalized()

    # Define an operator to measure the current after the barrier.
    hoppings = [(lat(78, 0), lat(77, 0))]
    current_operator = kwant.operator.Current(syst, where=hoppings)

    # Set occupation T = 0 and mu = -1 for both leads.
    occup = tkwant.manybody.lead_occupation(chemical_potential=-1)

    # Initialize the time-dependent manybody state. Use a lower
    # accuracy for adaptive refinement to speed up the calculation.
    state = tkwant.manybody.State(syst, tmax=max(times), occupations=occup,
                                  refine=False, combine=True)
    state.refine_intervals(rtol=0.3, atol=0.3)

    # Loop over timesteps and evaluate the current.
    currents = []
    for time in times:
        state.evolve(time)
        current = state.evaluate(current_operator)
        currents.append(current)

    # Plot the normalized current vs. time.
    if am_master():
        plt.plot(times, currents / currents[-1])
        plt.xlabel(r'time $t$')
        plt.ylabel(r'current $I$')
        plt.show()

if __name__ == '__main__':
    main()
