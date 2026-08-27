.. _onebody_advanced:

Advanced onebody settings
=========================

.. jupyter-execute::
    :hide-code:

    from cmath import exp
    from math import cos, sqrt, pi
    import numpy as np
    import matplotlib
    from matplotlib import pyplot as plt
    import kwant
    import tkwant

    def onsite_potential(site, time):
        return 1

    def create_system(L):

        # system building
        lat = kwant.lattice.square(a=1, norbs=1)
        syst = kwant.Builder()

        # central scattering region
        syst[(lat(x, 0) for x in range(L))] = 1
        syst[lat.neighbors()] = -1
        # time dependent onsite-potential V(t) at leftmost site
        syst[lat(0, 0)] = onsite_potential

        # add leads
        sym = kwant.TranslationalSymmetry((-1, 0))
        lead_left = kwant.Builder(sym)
        lead_left[lat(0, 0)] = 1
        lead_left[lat.neighbors()] = -1
        syst.attach_lead(lead_left)
        syst.attach_lead(lead_left.reversed())

        return syst

    syst = create_system(5).finalized()


We show some advanced settings for solving the onebody Schrödinger equation
which is based on :ref:`onebody`.
In the following, ``syst`` is a finalized kwant system with leads
and we import the onebody module from tkwant:

.. jupyter-execute::

    from tkwant import onebody


Boundary conditions
~~~~~~~~~~~~~~~~~~~

Special boundary conditions have to be provided in
order to solve the dynamic equations for an open quantum systems (with leads).
For ``onebody.WaveFunction`` they must be precalculated:

.. jupyter-execute::

    boundaries = [tkwant.leads.SimpleBoundary(tmax=500)] * len(syst.leads)
    scattering_states = kwant.wave_function(syst, energy=1, params={'time':0})
    lead, mode = 0, 0
    psi_st = scattering_states(lead)[mode]
    psi = onebody.WaveFunction.from_kwant(syst, psi_st, boundaries=boundaries, energy=1.)

For the scattering state solver boundary conditions are calculated on the fly.
One can provide different boundary conditions by the keyword ``boundary``


.. jupyter-execute::

    boundaries = [tkwant.leads.SimpleBoundary(tmax=500)] * len(syst.leads)
    psi = onebody.ScatteringStates(syst, energy=1, lead=0, boundaries=boundaries)[mode]

For closed quantum systems (without leads), no boundary conditions are needed.

.. seealso::
    A tutorial on boundary conditions is given in :ref:`boundary`.
    An example script which shows alternative boundary conditions is given in :ref:`alternative_boundary_conditions`.


Time integration
~~~~~~~~~~~~~~~~

The time integration can be changed by prebinding values with the module
``functool.partial`` to the onebody solver. In the current example, we
change the relative tolerance ``rtol`` of the time-stepping algorithm:

.. jupyter-execute::

    import functools as ft
    solver_type = ft.partial(tkwant.onebody.solvers.default, rtol=1E-5)
    psi = onebody.WaveFunction.from_kwant(syst=syst, boundaries=boundaries,
                                          psi_init=psi_st, energy=1.,
                                          solver_type=solver_type)

Time-dependent perturbation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the method ``onebody.WaveFunction.from_kwant()`` is used,
the time-dependent perturbation :math:`W(t)` is extracted from the Hamiltonian
of a Kwant system. By defaut, Tkwant uses cubic spline interpolation to interpolate
:math:`W(t)` in time with a static discretization time :math:`dt`.
The interpolation is used for performance reasons,
in order to minimize the number of calls to Kwant.

One can change the discretization time :math:`dt`, which by default is 
:math:`dt = 1`, to a different value:

.. jupyter-execute::

    import functools as ft
    perturbation_type = ft.partial(tkwant.onebody.kernels.PerturbationInterpolator, dt=0.5)
    psi = onebody.WaveFunction.from_kwant(syst=syst, psi_init=psi_st, energy=1.,
                                          boundaries=boundaries,
                                          perturbation_type=perturbation_type)

Setting :math:`dt = 0` will switch off interpolation and always evaluate the exact :math:`W(t)` function.
Alternatively, one can switch off interpolation directly with

.. jupyter-execute::

    psi = onebody.WaveFunction.from_kwant(syst=syst, psi_init=psi_st, energy=1.,
                                          boundaries=boundaries,
                                          perturbation_type=tkwant.onebody.kernels.PerturbationExtractor)

Saving and restarting states
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes we might like to save a state in order to resume a calculation
on a later stage. An easy way is to to use the ``pickle`` package:

.. jupyter-execute::

    import pickle
    saved = pickle.dumps(psi)

The saved object ``saved`` can be stored.
Recovering the state later on in order to continue the
calculation is possible by using

.. jupyter-execute::

    new_psi = pickle.loads(saved)

See :ref:`restarting` for the complete code.
Saving a state with ``pickle`` might not work for certain non-python kernels like
``onebody.kernel.Simple`` and ``onebody.kernel.SparseBlas``.

.. seealso::
    An example script showing the restarting of states is given in :ref:`restarting`.
