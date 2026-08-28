:orphan:

.. _closed_system:

Evolution of an eigenstate of a finite 2D system subject to a time-dependent gate
=================================================================================

Problem formulation
-------------------
Evolving single-particle states forward in time in a closed system,
and calculating the expectation value of the radial position operator.
The Hamiltonian is

.. math::


       H(t) = \sum_{ij \in R} 4 \gamma |i,j \rangle \langle i,j | 
       -  e^{i B y_i} \gamma  (|i+1,j \rangle \langle i,j | + \text{h.c.})
       -   \gamma (|i,j + 1 \rangle \langle i,j | + \text{h.c.})
       + \sum_{ij \in R_t}  r_{ij} V(t) \gamma  |i,j  \rangle \langle i,j |

with :math:`r_{ij} = \sqrt{x_i^2 + y_i^2}`, :math:`V(t) = V (1 - \cos(t))`,
:math:`\gamma` the hopping integral and *B* is the magnetic field strenght.
The system is defined with a circular shape with radius *R*
and :math:`R_t` is some smaller circle inside (sites in red) where the time-dependent perturbation is applied.

We solve the eigenvalue problem

.. math::

       H(t=0) \psi_0  = E \psi_0

and evolve eigenstate with the lowest energy in time with initial condition
:math:`\psi(t=0) = \psi_0` with the time-dependent Schrödinger equation.
The evolution of the radial density

.. math::

       n(t) = \sum_{i,j} r_{ij} \psi^*(t, x_i) \psi(t, x_j)
        

is plotted over time.

**tkwant features highlighted**

-  Use of ``tkwant.onebody.WaveFunction`` to solve the time-dependent Schrödinger
   equation for a closed system.

.. jupyter-execute:: closed_system.py

.. seealso::
    The complete source code of this example can be found in
    :download:`closed_system.py <closed_system.py>`.
