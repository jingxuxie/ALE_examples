:orphan:

.. _fabry_perot:

Second example: Fabry-Perot interferometer
=========================================

We consider an infinite one-dimensional chain with nearest-neighbor hopping,
in which two potential barriers A and B form a Fabry-Perot cavity. 
A sketch of the system is

.. image:: fabry_perot_grid.png

At time :math:`t = 0`, the electric potential :math:`V(t)` 
of the left electrode is suddenly raised from zero
to a finite value, which is taken into account by a 
time-dependent coupling element (shown in red) between the left electrode and the central system.
We want to study the transient
regime of the current :math:`I(t)` before it eventually reaches its
stationary value. This system has been studied in Ref. `[1] <#references>`__.
The actual simulation script in this tutorial is taken from Ref. `[2] <#references>`__,
but simulation time and accuracy are both reduced in this tutorial
in order to speed up the calculation. The entire simulation script is:

 .. jupyter-execute:: fabry_perot.py

.. seealso::
    The complete source code of this example can be found in
    :download:`fabry_perot.py <fabry_perot.py>`.

The result of the simulation shows the current increases through plateaus that
correspond to the different trajectories of the cavity. The first plateau corrsponds to a
direct transmission, whereas the second one is due to
reflection at B followed by reflection at A then transmission. For longer simulation times,
this series continues until a stationary current value is reached, 
see Refs. `[1, 2] <#references>`__.
Another detail is that on each plateau, the current oscillates with a frequency :math:`e V_b / h`,
where :math:`V_b` is the stationary value of the electric potential :math:`V(t)`.

.. warning::

    The examples in this section take several minutes on a single core desktop computer.
    To speed up the computation the script can be run in parallel, see section :ref:`mpi`.

References
----------

[1] B. Gaury, J. Weston, X. Waintal,
`The a.c. Josephson effect without superconductivity 
<https://www.nature.com/articles/ncomms7524>`__, 
Nat. Commun. **6**, 6524 (2015).
`[arXiv] <https://arxiv.org/abs/1407.3911>`__

[2]  T. Kloss, J. Weston, B. Gaury, B. Rossignol, C. Groth and X. Waintal,
Tkwant: a software package for time-dependent quantum transport.

