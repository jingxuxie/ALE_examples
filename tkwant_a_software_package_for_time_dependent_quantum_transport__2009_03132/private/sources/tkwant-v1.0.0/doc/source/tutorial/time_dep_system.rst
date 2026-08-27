.. _time_dep_system:

Time-dependent potentials and pulses
====================================

Tkwant uses Kwant to define the Hamiltonian of the tight-binding system.
We show in the following how time-dependent onsite and coupling elements
are defined. The latter can be used to simulate the injection of voltage
pulses through the lead electrodes.

Time dependent onsite elements
------------------------------

Time-dependent gate potentials, aka :math:`V_g(t)` in :ref:`getting_started`, 
act directly on the onsite elements of the Hamiltonian.
As an example, we define an infinitly long one-dimensional chain.
The central scattering region has 20 lattice sites (in black) and leads on both sides (in grey)
extend the system to :math:`\pm` infinity.
On lattice site 10 (depicted in red), an additional time-dependent
:math:`\sin(\omega t)` term is added to the onsite element. This can be done by defining
an appropriate onesite function, named ``onsite()`` in the example below:


.. jupyter-execute::

    import kwant
    from math import sin

    lat = kwant.lattice.square(a=1, norbs=1)
    syst = kwant.Builder()

    syst[(lat(x, 0) for x in range(20))] = 1
    syst[lat.neighbors()] = -1

    def onsite(site, fac, omega, time):
        return 1 + fac * sin(omega * time)

    # add the time-dependent onsite potential
    syst[lat(10, 0)] = onsite

    lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    lead[lat(0, 0)] = 1
    lead[lat.neighbors()] = -1
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())

    # plot the system
    kwant.plot(syst, site_color=lambda s: 'r' if s in [lat(10, 0)] else 'k', 
               lead_color='grey');

    syst = syst.finalized()


Kwant requires that the first element of
the ``onsite()`` function with name ``site`` is a 
`kwant.builder.Site <https://kwant-project.org/doc/1/reference/generated/kwant.builder.Site#kwant.builder.Site>`__ 
instance, while the other arguments are optional.
When initializing the solver ``tkwant.manybody.State`` the optional parameters
must be set by the ``params`` dictionary. Whereas the names for these optional parameters
are arbitrary, the name ``time`` is particular and will be interpreted
by Tkwant as the actual time variable.

.. jupyter-execute::

    import tkwant
    state = tkwant.manybody.State(syst, tmax=100, params={'fac':0.1, 'omega':0.5})

The position of the ``time`` variable within the optional parameters in 
the ``onsite()`` function is arbitrary.

.. seealso::
    An example script which a time-dependent onsite potential is
    :download:`1d_wire_onsite.py <../../examples/1d_wire_onsite.py>`.
    An example using optional parameters can be found in
    :download:`fabry_perot.py <fabry_perot.py>`.


Time dependent coupling elements
--------------------------------
Time-dependent coupling elements of the Hamiltonian can be defined quite similar.
Again, we use an infinitly long one-dimensional chain with a central
scattering region of 20 lattice sites (in black) as an example. The coupling element between
matrix element 9 and 10 (highlighted in red) has an additional time-dependent
:math:`\sin(\omega t)` term. This can be done by defining
a coupling function, named ``coupling()`` in the example below:


.. jupyter-execute::

    import kwant
    from math import sin

    lat = kwant.lattice.square(a=1, norbs=1)
    syst = kwant.Builder()

    syst[(lat(x, 0) for x in range(20))] = 1
    syst[lat.neighbors()] = -1

    def coupling(site1, site2, fac, omega, time):
        return -1 + fac * sin(omega * time)

    # add the time-dependent coupling element
    time_dependent_hopping = (lat(9, 0), lat(10, 0))
    syst[time_dependent_hopping] = coupling

    lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    lead[lat(0, 0)] = 1
    lead[lat.neighbors()] = -1
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())

    # plot the system
    kwant.plot(syst, site_color='k', lead_color='grey',
               hop_lw=lambda a, b: 0.3 if (a, b) in [time_dependent_hopping] else 0.1,
               hop_color=lambda a, b: 'red' if (a, b) in [time_dependent_hopping] else 'k');

    syst = syst.finalized()

Kwant requires that the first two elements of
the ``coupling()`` function to be instances of 
`kwant.builder.Site <https://kwant-project.org/doc/1/reference/generated/kwant.builder.Site#kwant.builder.Site>`__ .
The rest is similar to above example with the time-dependent onsite elements.

.. jupyter-execute::

    import tkwant
    state = tkwant.manybody.State(syst, tmax=100, params={'fac':0.1, 'omega':0.5})

Voltage pulses through a lead
-----------------------------

While the lead Hamiltonian does not depend explicitly on time, voltage
pulses through a lead can be simulated by time-dependent
coupling elements between the lead and system.
In the current example,
a time dependent potential drop is injected at a position :math:`i_b`, such that the
system Hamiltonian becomes

.. math::


       \hat{H}(t) =\sum_{ij} \gamma_{ij} c^\dagger_i c_i + \sum_i w(t) \theta(i_b - i) c^\dagger_i c_i

:math:`\theta(x)` is the Heaviside function and :math:`w(t)` an
arbitrary function parametrizing the time-dependent perturbation that we
like to apply to the system. In this example we choose a Gaussian
function

.. math::


       w(t) =  v_p e^{- ((t - t_0) / \tau)^2}

where :math:`v_p` is some strenght and :math:`\tau` accounts for the
width of the pulse. Note the convention that the time-dependent
perturbation has to start after time :math:`t=0` and we have introduced a shift
:math:`t_0` that should be chosen large enought
to switch on the perturbation adiabatically. 
One can absorb the
effect of the time-dependent perturbation by a gauge transform. Defining
the integrated pulse

.. math::


       \phi(t) = (e / \hbar) \int_{- \infty}^t dt' w(t') = A (1 + \textrm{erf}( (t - t_0) / \tau)), \qquad A = (e / \hbar ) v_p \tau \sqrt{\pi}/2 , 

we just have to rewrite the coupling :math:`\gamma` between site
:math:`i_b` and :math:`i_b + 1` by the time dependent coupling
:math:`\gamma(t)`:

.. math::


       \gamma \rightarrow \gamma(t) = \gamma e^{- i \phi(t)}

In the following code we define the function :math:`\phi(t)` named
``gaussian`` and replace the coupling between site 0 and 1 by the time
dependent coupling

.. jupyter-execute::

    import kwant
    import cmath
    from scipy.special import erf

    def make_system(a=1, gamma=1.0, W=10, L=30):

        lat = kwant.lattice.square(a=a, norbs=1)
        syst = kwant.Builder()

        def gaussian(time):
            t0 = 100
            A = 0.00157
            tau = 24
            return A * (1 + erf((time - t0) / tau))

        # time dependent coupling with gaussian pulse
        def coupling_nn(site1, site2, time):
            return - gamma * cmath.exp(- 1j * gaussian(time))

        #### Define the scattering region. ####
        syst[(lat(x, y) for x in range(L) for y in range(W))] = 4 * gamma
        syst[lat.neighbors()] = -gamma
        # time dependent coupling between two sites 0 and 1
        time_dependent_hoppings = [(lat(0, y), lat(1, y)) for y in range(W)]
        syst[time_dependent_hoppings] = coupling_nn

        #### Define and attach the leads. ####
        # Construct the left lead.
        lead = kwant.Builder(kwant.TranslationalSymmetry((-a, 0)))
        lead[(lat(0, j) for j in range(W))] = 4 * gamma
        lead[lat.neighbors()] = -gamma

        # Attach the left lead and its reversed copy.
        syst.attach_lead(lead)
        syst.attach_lead(lead.reversed())

        return syst, time_dependent_hoppings

    syst, time_dependent_hoppings = make_system()

    kwant.plot(syst, site_color='k', lead_color='grey',
               hop_lw=lambda a, b: 0.3 if (a, b) in time_dependent_hoppings else 0.1,
               hop_color=lambda a, b: 'red' if (a, b) in time_dependent_hoppings else 'k');


The special case of a time dependent coupling between the sites at the
system-lead interface shown above can be written in more compact form.
We first defines a system as before, but without the time dependent
part.

.. jupyter-execute::

    import kwant

    def make_system(a=1, gamma=1.0, W=10, L=30):

        lat = kwant.lattice.square(a=a, norbs=1)
        syst = kwant.Builder()

        #### Define the scattering region. ####
        syst[(lat(x, y) for x in range(L) for y in range(W))] = 4 * gamma
        syst[lat.neighbors()] = -gamma

        #### Define and attach the leads. ####
        # Construct the left lead.
        lead = kwant.Builder(kwant.TranslationalSymmetry((-a, 0)))
        lead[(lat(0, j) for j in range(W))] = 4 * gamma
        lead[lat.neighbors()] = -gamma

        # Attach the left lead and its reversed copy.
        syst.attach_lead(lead)
        syst.attach_lead(lead.reversed())

        return syst

The time dependent couplings are added by

.. jupyter-execute::

    import tkwant
    from scipy.special import erf

    def gaussian(time):
        t0 = 100
        A = 0.00157
        tau = 24
        return A * (1 + erf((time - t0) / tau))

    syst = make_system()
    added_sites = tkwant.leads.add_voltage(syst, 0, gaussian)

In fact, the routine adds new sites at the system-lead interface and
modifies ``syst``. Note that ``syst`` must not be finalized. We can also
skip ``added_sites`` and call ``tkwant.leads.add_voltage`` without
return argument, if we are not interested in the added sites. The second
function argument of ``tkwant.leads.add_voltage`` corresponds to the
lead number, here ``0``, where the pulse is injected. We can show the
new sites with time-dependent couplings (in red) if we plot the system.

.. jupyter-execute::

    interface_hoppings = [(a, b)
                          for b in added_sites
                          for a in syst.neighbors(b) if a not in added_sites]
    kwant.plot(syst, site_color='k', lead_color='grey',
               hop_lw=lambda a, b: 0.3 if (a, b) in interface_hoppings else 0.1,
               hop_color=lambda a, b: 'red' if (a, b) in interface_hoppings else 'k');


Note that in fact the system is not exactly the same as before due to
the additional sites (at x position -1), that were added. We could have constructed the
system with ``syst = make_system(L=29)`` to recover exactly the same
length as in the example before.

.. seealso::
    An example script where a voltage pulses is injected through a lead is
    :download:`fabry_perot.py <fabry_perot.py>`.
