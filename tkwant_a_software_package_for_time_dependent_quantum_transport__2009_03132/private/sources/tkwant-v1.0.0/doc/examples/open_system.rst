:orphan:

.. _open_system:

Evolution of a scattering state under a voltage pulse in a quantum dot
======================================================================

Problem formulation
-------------------

We consider a circular shaped central scattering region with two leads attached on the left
and on the right-hand side as shown below.
The system is perturbed by a time-dependent voltage pulse :math:`V_p(t)`
which is injected into the left lead. We evolve a single onebody scattering states of the system forward in time
and calculate the expectation value of the current.

Explicitly, the Hamiltonian is

.. math::

       \hat{H}(t) = \sum_{ij} \left[ 4 \gamma |i,j \rangle \langle i,j | 
       -  \gamma (|i+1,j \rangle \langle i,j | 
        + \text{h.c.} ) \right]
       + \sum_{j} \left[ (e^{i \phi(t)} + 1) \gamma (|i_p ,j  \rangle \langle i_p + 1, j | + \text{h.c.} \right]


The second term of :math:`\hat{H}(t)` accounts for the time-dependent voltage pulse

.. math::

       V_p(t) = \frac{V}{2} \left ( 1 - \cos\left (\frac{\pi t}{\tau} \right) \right)

such that the phase is

.. math::

       \phi(t) = (e/\hbar) \int_{0}^t d t' V_p(t')  = \frac{e V}{2 \hbar} \left ( t - \frac{\tau}{\pi} \sin\left (\frac{\pi t}{\tau} \right) \right).



The time-dependent couplings between the system and the left lead 
(between the lattice positions :math:`i_p = -10` and :math:`i_p + 1 = -9`),
are highlighed in red in the figure below.


The current in positive *x* direction through a system-lead coupling element is

.. math::

       j_{y} (t) = - 2 i \text{Im}  \psi_\alpha^\dagger (t) H_{\alpha \beta} \psi_\beta (t)  

where :math:`\alpha \equiv (i_p, y)` and :math:`\beta \equiv (i_p+1, y)` label the grid position in *x* and *y* direction.
Summing in *y* direction, we plot the total current through the system-lead interface

.. math::

       I(t) = \sum_{y_i} j_{y_i} (t)




**tkwant features highlighted**

-  Use of ``tkwant.leads.add_voltage`` to add time-dependence to leads.
-  Use of ``tkwant.onebody.WaveFunction`` to solve the time-dependent Schrödinger
   equation for an open system.

.. jupyter-execute:: open_system.py

.. seealso::
    The complete source code of this example can be found in
    :download:`open_system.py <open_system.py>`.

