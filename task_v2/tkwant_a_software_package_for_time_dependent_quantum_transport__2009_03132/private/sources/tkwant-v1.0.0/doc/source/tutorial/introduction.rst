.. _introduction:

Introduction
============

Tkwant is a Python package for the simulation of quantum nanoelectronics devices on which
external time-dependent perturbations are applied. Tkwant is an extension of the `Kwant <https://kwant-project.org>`_  package
and can handle the same types of systems: discrete tight-binding like
models that consist of an arbitrary central region connected to semi-infinite electrodes, also called leads.
For such systems, tkwant provides algorithms to simulate the time-evolution of manybody expectation values, as e.g. densities and currents.

.. _system:

.. figure:: scattering_region.png
    :width: 500px


    Sketch of a typical open quantum system which can
    be simulated with Tkwant. A central scattering region (in
    black) is connected to several leads (in grey). Each lead
    represents a translationally invariant, semi-infinite system in
    thermal equilibrium. Sites and hopping matrix elements are
    represented by dots and lines. The regions in red indicate a
    time-dependent perturbation, in this example a global voltage
    pulse :math:`V_p (t)` on lead 0 and a time-dependent voltage :math:`V_g (t)` on
    a gate inside the scattering region.
    The figure is taken from Ref. `[1] <#references>`__.


**Input**: A tight-binding Hamiltonian of generic form

.. math::

       \hat{H}(t) = \sum_{ij} H_{ij}(t) \hat{c}^\dagger_i \hat{c}_j

as well as the chemical potential :math:`\mu` and the temperature :math:`T` in each lead.

**Output**: Time-dependent manybody expectation values, such as
the electron density :math:`n_i(t) = \langle \hat{c}^\dagger_i \hat{c}_i \rangle`
an currents 
:math:`j_i(t) = i[\langle \hat{c}^\dagger_i \hat{c}_{i+1} \rangle - \langle \hat{c}^\dagger_{i+1} \hat{c}_{i} \rangle]`.
We refer to Tkwant's main paper Ref. `[1] <#references>`__  for the technical background.

References
----------

[1]  T. Kloss, J. Weston, B. Gaury, B. Rossignol, C. Groth and X. Waintal,
Tkwant: a software package for time-dependent quantum transport.
