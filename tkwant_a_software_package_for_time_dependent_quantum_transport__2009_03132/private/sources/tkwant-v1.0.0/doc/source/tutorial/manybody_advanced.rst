.. _manybody_advanced:

Advanced manybody settings
==========================

.. jupyter-execute::
    :hide-code:

    # do not show the system, which is not important in our case.
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.special import erf
    import cmath
    import functools

    import kwant
    import kwantspectrum
    import tkwant

    def gaussian(time):
        t0 = 100
        A = 0.00157
        sigma = 24
        return A * (1 + erf((time - t0) / sigma))

    # time dependent coupling with gaussian pulse
    def coupling_nn(site1, site2, time):
        return - cmath.exp(- 1j * gaussian(time))

    def make_system(a=1, W=1, L=2):

        lat = kwant.lattice.square(a=a, norbs=1)
        syst = kwant.Builder()

        #### Define the scattering region. ####
        syst[(lat(x, y) for x in range(L) for y in range(W))] = 1
        syst[lat.neighbors()] = -1
        # time dependent coupling between two sites 0 and 1
        for y in range(W):
            syst[lat(0, y), lat(1, y)] = coupling_nn

        #### Define and attach the leads. ####
        # Construct the left lead.
        lead = kwant.Builder(kwant.TranslationalSymmetry((-a, 0)))
        lead[(lat(0, j) for j in range(W))] = 1
        lead[lat.neighbors()] = -1

        # Attach the left lead and its reversed copy.
        syst.attach_lead(lead)
        # syst.attach_lead(lead.reversed())

        return syst

    syst = make_system().finalized()

    density_operator = kwant.operator.Density(syst)
    state = tkwant.manybody.State(syst, tmax=10)

    def calc_my_boundstates():  # a routine to mimic boundstates
        tasks = {100: tkwant.onebody.Task(weight=0.1, energy=0.5, lead=None, mode=None)}
        psi = {key: tkwant.onebody.ScatteringStates(syst, energy=task.energy,
                                                    lead=0, tmax=10)[0]
               for key, task in tasks.items()}
        return psi, tasks


We show some advanced settings for solving the manybody Schrödinger equation
which is based on :ref:`manybody`.
In the following, ``syst`` is a finalized kwant system with leads
and we import the manybody module from tkwant:

.. jupyter-execute::

    from tkwant import manybody


Lead occupation
---------------

The occupation of the manybody state depends on the temperature :math:`T`, the chemical
potential :math:`\mu`, as well as the distribution function :math:`f` of the leads.
The function ``manybody.lead_occupation()`` offers an easy way to set the lead occupation.
This is possible both in the "high-level" approach with ``manybody.State()`` and
also in the "low-level" approach with ``manybody.WaveFunction()``, see :ref:`manybody`.
The default occupation

.. jupyter-execute::

    occupation = manybody.lead_occupation()

corresponds to :math:`T = \mu = 0` and 
noninteracting Fermi-Dirac distribution function.
In the case that several leads are attached to the system, the occupation
can be a sequence of ``occupation`` objects, one for each lead.
If only one ``occupation`` object is used, as in this example, the occupation
is assumed to be identical for each lead.

In the following we
show how to change the default behavior of ``manybody.lead_occupation()``.

Chemical potential
~~~~~~~~~~~~~~~~~~

The chemical potential (:math:`\mu`) is zero by default. In the following
example, we set the chemical potential of the lead to the finite value
:math:`\mu = 1`:

.. jupyter-execute::

    occupation = manybody.lead_occupation(chemical_potential=1.)

For zero temperature and Fermi Dirac distribution, the chemical potential is identical to the Fermi energy.


Temperature
~~~~~~~~~~~

The temperature (:math:`T`) is zero by default. In the following
example, we set the temperature of the lead to the finite value
:math:`T = 0.5`:

.. jupyter-execute::

    occupation = manybody.lead_occupation(temperature=0.5)

Distribution function
~~~~~~~~~~~~~~~~~~~~~

The distribution function :math:`f_\alpha(E)` can be changed with the keyword
``distribution``. As an example, we set up a lead with Bose distribution
at finite temperature:

.. jupyter-execute::

    def bose_function(mu, T, energy):
        return 1 / (exp((energy - mu) / T) - 1)

    occupation = manybody.lead_occupation(temperature=0.5, distribution=bose_function)

Note that the distribution function :math:`f` must have the calling
signature ``(chemical_potential, temperature, energy)``.

Energy range
~~~~~~~~~~~~

Upper and lower energy values can be set with the keyword ``energy_range``,
which is a sequence of intervals in the form ``(emin, emax)``.
If present, only modes with energies ``emin``
:math:`\leq E_n \leq` ``emax`` are considered. As an example, we select
only the modes with energies :math:`0.4 \leq E_n \leq 0.6`:

.. jupyter-execute::

    occupation = manybody.lead_occupation(energy_range=[(0.4, 0.6)])

Include / exclude bands
~~~~~~~~~~~~~~~~~~~~~~~

The statistical average can be performed only over a subset of energy
bands :math:`E_n`. Specifying the keyword ``bands`` with a list of band
indices, only the bands with band index :math:`n` specified in the list
are included. As an example, we perform the statistical average only
over the two lowest energy :math:`E_n` bands with band index
:math:`n = 0` and 1:

.. jupyter-execute::

    occupation = manybody.lead_occupation(bands=[0, 1])

Note that the provided band indicees must be in the physically valid
range, that is, they must not exceed the maximum number of bands.


Include / exclude leads
~~~~~~~~~~~~~~~~~~~~~~~

For system with several leads, the occupation passed to
``manybody.State()`` can be a sequence with one element per leads. If a
lead should not contribute to the statistial average, the corresponding
element of the ``occupation`` sequence must be set to ``None``.
In the following example, our system is expected to has two leads,
but only the contribution of the lead with index 0 is taken into account:

.. jupyter-execute::

    occup = manybody.lead_occupation()
    occupations = [occup, None]

Occupation data format
~~~~~~~~~~~~~~~~~~~~~~

The function ``manybody.lead_occupation()`` 
returns a ``manybody.Occupation`` instance with the physical
information on how to perform the statistical average. One can directly inspect the information
stored:

.. jupyter-execute::

    occupation = manybody.lead_occupation()
    print(occupation)

The ``occupation`` object is used to extract energy cutoffs in order to
calculate quadrature intervals and boundary conditions. It also
stores the distribution function :math:`f(E)`.



Numerical integration
---------------------

Quadrature intervals for the manybody integral are calculated from the lead occupation
and the lead spectrum:

.. jupyter-execute::

    spectra = kwantspectrum.spectra(syst.leads)
    occupation = manybody.lead_occupation()
    intervals = manybody.calc_intervals(spectra, occupation)

This sequence is part of the pre-processing in the "low-level" approach, see :ref:`manybody`.
In the "high-level" approach, one can precalculate the intervals and pass then to the manybody state,
in order to bypass the default interval calculation in ``manybody.State()``:

.. jupyter-execute::

    tmax = 10
    spectra = kwantspectrum.spectra(syst.leads)
    occupation = manybody.lead_occupation()
    intervals = manybody.calc_intervals(spectra, occupation)
    state = manybody.State(syst, tmax, occupation, intervals=intervals)

This mechanism is especially useful to directly manipulate intervals in the
intervals list.
A second way to manipulate the interval calculation of ``manybody.State()``
is to change the default interval type. The interval type can be passed also
by the ``interval`` argument:

.. jupyter-execute::

    state = manybody.State(syst, tmax, occupation, intervals=manybody.Interval)

``manybody.Interval`` is the default data class to construct the quadrature interval.
One can change the default to alter the behavior, as will be shown in the following.

Quadrature order
~~~~~~~~~~~~~~~~

The quadrature order can be changed via:

.. jupyter-execute::

    import functools
    interval_type = functools.partial(manybody.Interval, order=10)
    intervals = manybody.calc_intervals(spectra, occupation, interval_type=interval_type)

The list of intervals can be used further in the "low-level" approach or
passed to ``manybody.State()`` in the "high-level" approach:

.. jupyter-execute::

    state = manybody.State(syst, tmax, occupation, intervals=intervals)

Alternatively, for the second way of the "high-level", the modified ``manybody.Interval`` 
data class can passed directly to the manybody state:

.. jupyter-execute::

    import functools
    interval_type = functools.partial(manybody.Interval, order=10)
    state = manybody.State(syst, tmax, occupation, intervals=interval_type)

The order is usually taken between 10 and 20. If the integration is not
accurate enough one should rather divide each interval into subintervals
with the keyword ``number_subintervals``.


Interval subdivision
~~~~~~~~~~~~~~~~~~~~

**Momentum split**
Each momentum quadrature interval can be equidistantly divided into :math:`n`
subintervals to increase the numerical accuracy. Here we divide into
:math:`n=10` subintervals with the keyword ``number_subintervals``:

.. jupyter-execute::

    # (kmin, kmax) -> [(kmin, k_0), (k_0, k_1).. (k_{n-1}, kmax)]
    intervals = manybody.split_intervals(intervals, number_subintervals=10)


**Energy split**
Splitting intervals in energy space is possible by using `energy_range`.
The snippet below is to reproduce older calculations performed with
energy integrations on an energy interval splitted equidistantly into subintervals (here 10).

.. jupyter-execute::

    from itertools import tee

    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    chemical_potential = 1

    # energy interval split (0, 1) -> [(0, 0.1), (0.1, 0.2).. (0.9, 1)]
    energy_range = [i for i in pairwise(np.linspace(0, chemical_potential, 11))]
    occupation = manybody.lead_occupation(chemical_potential,
                                          energy_range=energy_range)

    Interval = functools.partial(manybody.Interval, integration_variable='energy')
    intervals = manybody.calc_intervals(spectra, occupation, interval_type=Interval)

``intervals`` is now already a sequence of 10 intervals, no additional split
with ``manybody.split_intervals`` is needed. If
``integration_variable="momentum"``, the split is still performed in the energy
range, but the quadrature will be integrate over momentum.


Quadrature rule
~~~~~~~~~~~~~~~

The quadrature rule can be changed via:

.. jupyter-execute::

    import functools
    interval_type = functools.partial(manybody.Interval, quadrature = 'gausslegendre')
    intervals = manybody.calc_intervals(spectra, occupation, interval_type=interval_type)

.. note::

    Changing the quadrature rule is only useful in the low-level approach. 
    In ``manybody.State()`` the  error estimate and the
    refinement is based on Gauss-Kronrod quadrature, which cannot be changed.
    If intervals with another rule than Gauss-Kronrod are passed to ``manybody.State()``,
    these intervals do not take place for refinement and error estimate.


Quadrature error
~~~~~~~~~~~~~~~~

The solver ``manybody.State()`` has a method ``estimate_error()`` to estimate
the quadrature error. Here we show an alternative error estimate in the low-level approach.
We define the integration error (:math:`\delta`) as:

.. math::


       \delta = \text{max}(|\rho_{n} - \rho_{2n+1}|)

where :math:`\rho_{n}` is the density calculated with the lower
(:math:`n`) order rule and :math:`\rho_{2 n + 1}` is the density
calculated with the higher (:math:`2 n +1`) quadrature rule of the Gauss-Kronrod method.

.. jupyter-execute::

    def maximal_absolute_error(result):
        low_order, high_order = result
        return np.max(np.abs(low_order - high_order))

    intervals = manybody.calc_intervals(spectra, occupation)
    tasks = manybody.calc_tasks(intervals, spectra, occupation)
    emin, emax = manybody.calc_energy_cutoffs(occupation)
    boundaries = tkwant.leads.automatic_boundary(spectra, tmax, emin=emin, emax=emax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries)
    state = manybody.WaveFunction(psi_init, tasks)
    density = state.evaluate(density_operator)
    print('integration error delta= {}'.format(maximal_absolute_error(density)))

The quadrature rule applied to each interval can be accessed using
the keyword ``quadrature``. Note that the adaptive state ``manybody.State``
needs a Gauss-Kronrod like rule for the error estimate.


Energy vs. momentum integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The expectation value of an observable :math:`\hat{\mathbf{A}}` in the manybody state
is defined as

.. math::

    \langle \hat{\mathbf{A}} \rangle (t) 
    = \sum_{\alpha} \int \frac{dE}{2 \pi} f_\alpha(E)  \psi_{\alpha E}^*(t,i) \mathbf{A}_{ij} \psi_{\alpha E}(t,j)

The integrand of the above energy integral diverges weakly as each
scattering wave function scales as :math:`\sim 1/\sqrt{v_\alpha(E)}`,
with velocities :math:`v_\alpha(E) = \frac{d E_{\alpha}}{d k}` in the
vicinity of the band openings. We can rewrite the integral in the form

.. math::

    \langle \hat{\mathbf{A}} \rangle (t) 
    = \sum_{\alpha} \int_{k_{{\rm min}, \alpha}}^{k_{{\rm max}, \alpha}} \frac{dk}{2 \pi} f_\alpha(E_\alpha(k)) v_\alpha(k) \psi_{\alpha k}^*(t,i) \mathbf{A}_{ij} \psi_{\alpha k}(t,j)

which is analytically equivalent but performs better numerically, as the
diverging points are eliminated.

One can switch between the two ways to perform the manybody average with the keyword ``integration_variable``.
By default, ``integration_variable`` = *momentum*, and the integration is performed over the momentum,
which corresponds the second equation.
With ``integration_variable`` = *energy* one switches to the first equation and integrates explicitly over

Intervals can be pre-calculated with

.. jupyter-execute::

    import functools
    interval_type = functools.partial(manybody.Interval, integration_variable='energy')
    intervals = manybody.calc_intervals(spectra, occupation, interval_type=interval_type)

Note that ``manybody.Intervals`` returned from ``manybody.intervals()`` always store
momentum intervals, independent of ``integration_variable``.

Alternatively, the integral type used by the manybody state is changed via

.. jupyter-execute::

    interval_type = functools.partial(manybody.Interval, integration_variable='energy')
    state = manybody.State(syst, tmax, occupation, intervals=interval_type)


Interval data format
~~~~~~~~~~~~~~~~~~~~

One can directly inspect the stored information of a quadrature interval:

.. jupyter-execute::

    intervals = manybody.calc_intervals(spectra, occupation)
    for interval in intervals:
        print(interval)

``lead`` and ``band`` corresonds to the lead respectively band index,
and ``kmin`` and ``kmax`` are the lower respectively upper momentum
values of the interval. The actual values change depending on the
specific problem. The other parameters have default values: ``order`` is
the quadrature order applied to the interval (generally the number of
point at which the interval is discretized) and ``quadrature`` is the
concrete quadrature rule that will be applied. ``integration_variable`` is an
additional information to switch between energy and momentum
integration.


Tasks data format
~~~~~~~~~~~~~~~~~

The routine ``calc_tasks()`` calculates the modes and weights for all intervals:

.. jupyter-execute::

    spectra = kwantspectrum.spectra(syst.leads)
    occupation = manybody.lead_occupation()
    intervals = manybody.calc_intervals(spectra, occupation)
    tasks = manybody.calc_tasks(intervals, spectra, occupation)

To be more precise, ``calc_tasks()`` returns a dictionary with
information about all one-body states and the corresponding weighting
factor. Each element in the dictionary corresponds to a onebody state
and looks like this:

.. jupyter-execute::

    for key, task in tasks.items():
        if key < 3:  # print only the first three tasks
            print(task)

For each set of ``(lead, mode, energy)`` attributes which are stored in each
``task`` element, the function
``manybody.calc_initial_state()`` calculates the corresponding
one-body scattering state :math:`\psi_{\alpha}(t=0, x)`:

.. jupyter-execute::

    tasks = manybody.calc_tasks(intervals, spectra, occupation)
    boundaries = tkwant.leads.automatic_boundary(spectra, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries)

that form the manybody state at the initial time *t=0*.
The initial state can be used as an initial state of manybody wave function 
``manybody.WaveFunction()``:

.. jupyter-execute::

    psi_init = manybody.calc_initial_state(syst, tasks, boundaries)
    state = manybody.WaveFunction(psi_init, tasks)

Evaluating an observable over
the manybody state, the state ``manybody.WaveFunction()`` will sum over
all one-body states present in the ``tasks`` list and weight each term
in the sum with the respective weight ``weight``.

.. note::

    Tasks can not passed to the "high-level" solver ``manybody.State``.
    This is because the quadrature error (via ``estimate_error()``)
    can be estimated only on intervals, not on individual evaluation points.
    Moreover,  ``psi_init`` is a dictionary, but which is distributed
    over all MPI ranks. We refer to the source code for technical details.

Time integration
~~~~~~~~~~~~~~~~

The time integration is performed at the level of onebody states. One
can change the default settings by prebinding values with the module
``functool.partial`` to the onebody state. In the current example, we
change the relative tolerance ``rtol`` of the time-stepping algorithm.
The first binding to ``solver_type`` changes the tolerance ``rtol`` of
the time integrator. The second binding defines a new onebody solver
``onebody_solver`` that uses this time integrator. The onebody solver
can be passed via keyword to one of the three solvers. Here we show the
example for ``manybody.State()``:

.. jupyter-execute::

    import functools
    solver_type = functools.partial(tkwant.onebody.solvers.default, rtol=1E-5)
    onebody_wavefunction_type = functools.partial(tkwant.onebody.WaveFunction.from_kwant, 
                                                  solver_type=solver_type)
    scattering_state_type = functools.partial(tkwant.onebody.ScatteringStates,
                                              wavefunction_type=onebody_wavefunction_type)
    state = manybody.State(syst, tmax=10, scattering_state_type=scattering_state_type)

A similar strategy is possible to change the onebody kernels
``onebody.kernels`` that evaluate the right-hand-side of the one-body
Schrödinger equations.


Retrieve one-body states
------------------------

The manybody state ``manybody.WaveFunction`` provides several methods
to retrieve the underlying one-body states. They can be useful for
realizing specific problems beyond the examples mentioned above.

State identifier
~~~~~~~~~~~~~~~~

The attribute ``state.tasks`` is a dictionary of all one-body states
stored in the ``state`` instance. The ``state.tasks`` dictionary is
identical on all MPI ranks. The key (:math:`\equiv \alpha`) uniquely labels each one-body state
:math:`\psi_{\alpha}(t)` :

.. jupyter-execute::

    state = manybody.WaveFunction(psi_init, tasks)
    keys = state.get_keys()
    print('number of one-body states inside manybody = {}'.format(len(keys)))
    print('keys={}'.format(keys))

State information
~~~~~~~~~~~~~~~~~

Further information about the one-body state :math:`\psi_{\alpha}(t)` can be found in the
``state.tasks`` dictionary. It contains the lead and the mode index, the
mode energy, as well as the weighting factor :math:`w_{\alpha, l}` in
the statistical average. As an example, we print the information for
one-body state corresponding to the key zero:

.. jupyter-execute::

    key = 0
    print(state.tasks[key])

One-body states
~~~~~~~~~~~~~~~

One-body states  :math:`\psi_{\alpha}(t)` 
can be retrieved using the ``get_state()`` method:

.. jupyter-execute::

    psi = state.get_onebody_state(key=0)

Note that the attribute ``state.psi`` is a dictionary of one-body states
that basically provides the same information. In parallel MPI
environments, however, some caution is required. When multiple ranks are
available ``manybody.State()`` distributes the one-body states to all
MPI ranks. Since each one-body state is unique, a particluar one-body
state is located only on one of all the available MPI ranks. Although
not currently implemented, ``manybody.State()`` could additionally use
dynamic load balancing in the future and redistribute the one-body
states at runtime. The ``get_state()`` method guarantees that the
requested state is always returned without worring about the MPI rank
distribution.

In addition, we would like to point out that the result of evaluating an
observable is independent from the distribution of the one-body states
on the MPI ranks (although the result is not bitwise identical due to
rounding errors), because the statistical average is taken over all
states listed in ``state.tasks``. Only the performance and memory
consumption might become bad, if the distribution to the MPI ranks is
not balanced.

Evolution time
~~~~~~~~~~~~~~

The current time of the state can be obtained via the attribute
``state.time``:

.. jupyter-execute::

    print('time= {}'.format(state.time))

The initial time of the manybody wavefunction ``manybody.WaveFunction`` is zero, so
that ``state.time=0`` after initialization. It is not checked if the time attributes in the
individual one-body states are similar or consistent, only backward-propagation
of the states in time is not allowd.
After calling ``state.evolve(time)`` all one-body states that compose the manybody wavefunction
have evolved to time ``time`` and also ``state.time`` equals ``time``.

Miscellaneous
-------------

Band structure
~~~~~~~~~~~~~~

The band spectra for all leads are calculated on demand inside
``manybody.State()``. An own spectrum can be passed to the state with
the keyword ``spectra``:

.. jupyter-execute::

    spectra = kwantspectrum.spectra(syst.leads)
    state = manybody.State(syst, tmax=10, spectra=spectra)

Boundary conditions
~~~~~~~~~~~~~~~~~~~

Boundary conditions are calculated internally for all leads of the
system. In order to provide own boundary conditions, they can be
precalculate and transferred to the state with keyword ``boundaries``:

.. jupyter-execute::

    boundaries = [tkwant.leads.SimpleBoundary(tmax=10)] * len(syst.leads)
    state = manybody.State(syst, boundaries=boundaries)

Initial state
~~~~~~~~~~~~~

Arbitrary initial states can be provided to the manybody state with the
keyword ``psi_init``. The state is simply a dictionary of one-body
states. In addition, a dictionary with the weighting factors for each
state must be provided with the keyword ``tasks``:

.. jupyter-execute::

    new_state = manybody.WaveFunction(psi_init=psi_init, tasks=tasks)

Note that the boundary condition is attached to each (initial) one-body
state that forms the manybody state. Therefore, one cannot redefine
boundary conditions by initializing ``manybody.State()`` from
``psi_init``. Passing the keywords ``boundary`` and/or ``tmax`` together
with ``psi_init`` leads to a ``ValueError``.

The time attribute ``new_state.time=0`` after initialization.
As stated above, is not checked if the time attributes in the
individual one-body states are similar or consistent.

Boundstates
~~~~~~~~~~~

The following code illustrates how to include boundstates in the manybody
dynamics. First, the boundstates are calculated in some user-written function,
here called ``calc_my_boundstates()``:

.. jupyter-execute::

    boundstate_psi, boundstate_tasks = calc_my_boundstates()

``boundstate_psi`` is a dictionary of all boundstate wavefunctions.
It has basically the same form as an initial manybody state calculated from
``manybody.calc_initial_state()``.
``boundstate_tasks`` contain the weighting factor and the energy of each
boundstate and is similar to the output of ``manybody.calc_tasks()``.

In the case that ``state`` is a manybody state instance created with
``manybody.State``, boundstates are easily added by the method
``add_boundstates()``:

.. jupyter-execute::

    state = manybody.State(syst, tmax)
    state.add_boundstates(boundstate_psi, boundstate_tasks)

In the case that the manybody state instance has been created with
``manybody.WaveFunction``, the boundstates must be added with the
function ``manybody.add_boundstates()``.
If the boundstates are not yet time dependent, they must first transformed
with ``make_boundstate_time_dependent``.
In both cases, the keys for the new boundstates must not be present in
the manybody state already.

