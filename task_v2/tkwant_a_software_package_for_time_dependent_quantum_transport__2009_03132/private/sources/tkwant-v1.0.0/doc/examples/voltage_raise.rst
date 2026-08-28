:orphan:

.. _voltage_raise:

Comparision between bias chemical potential and bias electrical potential
=========================================================================

We consider a circular shaped central scattering region with two leads attached on the left
and on the lower site as shown below. The left lead has an additional
bias potential :math:`V_b`. In second quantization, the Hamiltonian is

.. math::

    \hat{H}(t) =  \sum_{i,j} \gamma_{ij} \, \hat{c}^\dagger_i \hat{c}_j
    + \sum_{i < i_p} V_b \, \hat{c}^\dagger_i \hat{c}_i

where :math:`\gamma_{ii} = 4` and for nearest-neighbors :math:`\gamma_{ij} = -1`.
We are interested in the time-dependent current :math:`I(t)` through the coupling element
(highlighted in red in the system plot)
from the left lead to the central scattering region:

.. math::

    I(t)
    = - 2 \text{Im} \sum_{\alpha} \int \frac{dE}{2 \pi} f_\alpha(E) 
      \psi_{\alpha E}^*(t,i_p) \mathbf{H}_{i_p, i_p + 1} \psi_{\alpha E}(t,i_p + 1) 

Two different results are obtained whether the potential :math:`V_b`
is explicitly time dependent or not.
We refer to Ref. [1]_ for more information.


**Static voltage**

In the static case, the potential has a constant value :math:`V_b \equiv V = 0.5`.
One can calculate the constant value of the current directly from
the solution of above equations at the initial time :math:`t = 0`.


**Dynamic voltage pulse**

In the dynamic case the potential is zero at the initial time, but is switched on smoothly
to reach the similar value as in the static case. We parametrize the potential as
 
.. math::

       V_b(t) = 
        \begin{cases}
        0, & \text{for } t < 0\\
        \frac{V}{2} \left ( 1 - \cos\left (\frac{\pi t}{\tau} \right) \right) , & \text{for } 0 \leq t \leq
        \tau \\
        V , & \text{for } t > \tau
        \end{cases}

such that the phase is

.. math::

       \phi(t) = e/\hbar \int_{-\infty}^t d t' V_b(t') = 
        \begin{cases}
        0, & \text{for } t < 0\\
        \frac{e V}{2 \hbar} \left ( t - \frac{\tau}{\pi} \sin\left (\frac{\pi t}{\tau} \right) \right), & \text{for } 0 \leq t \leq
        \tau \\
        e V / \hbar (t - \tau / 2) , & \text{for } t > \tau
        \end{cases}

Performing a gauge transform, the time-dependent lead potential can be absorbed
in the time-dependent system-lead coupling element between :math:`i_b` and :math:`i_b + 1`:

.. math::

    \hat{H}(t) =  \sum_{i,j} \gamma_{ij} \, \hat{c}^\dagger_i \hat{c}_j
    - [e^{i \phi(t)} - 1 ] \, \hat{c}^\dagger_{i_b + 1} \hat{c}_{i_b} + \text{h.c.}

The result obtained from the static and from the dynamic case are shown below.


**tkwant features highlighted**

-  Use of ``tkwant.manybody.State``
-  Use of ``tkwant.leads.add_voltage`` to add time-dependence to leads.

.. jupyter-execute:: voltage_raise.py

.. seealso::
    The complete source code of this example can be found in
    :download:`voltage_raise.py <voltage_raise.py>`.

References
~~~~~~~~~~

.. [1] B. Gaury, J. Weston, M. Santin, M. Houzet, C. Groth and X. Waintal,
    `Numerical simulations of time-resolved quantum electronics 
    <https://www.sciencedirect.com/science/article/pii/S0370157313003451?via%3Dihub>`__, Phys. Rep.
    **534**, 1 (2014). `[arXiv] <https://arxiv.org/abs/1307.6419>`__


