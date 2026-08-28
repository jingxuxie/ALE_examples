:orphan:

.. _restarting:

Restarting calculations from previously saved results
=====================================================

The physical system in this example is similar to :ref:`open_system`.
For time arguments on the right of the dashed vertical line, the
result is calculated with the restarted wave function.

**tkwant features highlighted**

-  restarting calculations from previously saved results


**Saving**

.. jupyter-execute::

    import pickle
    import numpy as np

    import kwant
    import tkwant


    def circle(pos):
        (x, y) = pos
        radius = 10
        return x ** 2 + y ** 2 < radius ** 2


    def make_system(a=1, gamma=1.0):
        """Make a tight binding system on a single square lattice"""
        # `a` is the lattice constant and `gamma` the hopping integral
        # both set by default to 1 for simplicity.

        lat = kwant.lattice.square(a, norbs=1)

        syst = kwant.Builder()

        # Define the quantum dot
        syst[lat.shape(circle, (0, 0))] = 4 * gamma
        syst[lat.neighbors()] = -gamma

        lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
        radius = 10
        lead[(lat(0, j) for j in range(-radius // 2 + 1, radius // 2))] = 4 * gamma
        lead[lat.neighbors()] = -gamma

        syst.attach_lead(lead)
        syst.attach_lead(lead.reversed())

        return syst


    # time-dependent voltage on top of the leads
    def faraday_flux(time):
        return 0.05 * (time - 10 * np.sin(0.1 * time))

    syst = make_system()

    # add a time-dependent voltage to lead 0 -- this is implemented
    # by adding sites to the system at the interface with the lead and
    # multiplying the hoppings to these sites by exp(-1j * faraday_flux(time))
    extra_sites = tkwant.leads.add_voltage(syst, 0, faraday_flux)
    lead_syst_hoppings = [(s, site) for site in extra_sites
                          for s in syst.neighbors(site)
                          if s not in extra_sites]

    syst = syst.finalized()

    # create an observable for calculating the current flowing from the left lead
    current_operator = kwant.operator.Current(syst, where=lead_syst_hoppings, sum=True)

    tmax = 150
    times = np.linspace(0, tmax, 100)

    # create a time-dependent wavefunction that starts in a scattering state
    # originating from the left lead
    psi = tkwant.onebody.ScatteringStates(syst, energy=1., lead=0, tmax=tmax)[0]

    # evolve forward in time, calculating the current
    current = []
    for time in times:
        psi.evolve(time)
        current.append(psi.evaluate(current_operator))

    # now we want to "save" our progress. we also save the timesteps with the
    # calculated currents and the operator.
    pickle.dump((psi, times, current, current_operator), open('state.npy', "wb"))


**Restarting**

.. jupyter-execute::

    import pickle
    import numpy as np
    from matplotlib import pyplot as plt

    # pickle only saves the name reference to "faraday_flux", 
    # this function must be explicitly available.
    def faraday_flux(time):
        return 0.05 * (time - 10 * np.sin(0.1 * time))

    # load the previously saved state and for convenience also the same operator.
    psi, times, current, current_operator = pickle.load(open('state.npy', 'rb'))

    tmax = times[-1]
    times2 = np.linspace(tmax, 2 * tmax, 100)

    for time in times2:
        psi.evolve(time)
        current.append(psi.evaluate(current_operator))

    plt.plot(np.append(times, times2), current)
    plt.plot([tmax] * 2, [min(current), max(current)], 'k--')
    plt.xlabel(r'time $t$')
    plt.ylabel(r'current $I(t)$')
    plt.show()
