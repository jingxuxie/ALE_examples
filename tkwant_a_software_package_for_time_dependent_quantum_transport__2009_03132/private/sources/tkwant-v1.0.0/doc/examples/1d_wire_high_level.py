import tkwant
import kwant
import cmath
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

    state = tkwant.manybody.State(syst, max(times))

    density0 = state.evaluate(density_operator)

    for time in times:
        state.evolve(time=time)
        if time == 40:
            state.refine_intervals()
        error = state.estimate_error()
        density = state.evaluate(density_operator)
        if am_master():
            print('time={}, error={:10.4e}'.format(time, error))
            plt.plot(sites, density - density0, label='time={}'.format(time))

    if am_master():
        plt.legend()
        plt.xlabel(r'site position $i$')
        plt.ylabel(r'charge density $n$')
        plt.show()


if __name__ == '__main__':
    main()
