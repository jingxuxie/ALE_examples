.. _faq:

Frequently asked questions
==========================

.. specialnote:: The tkwant package cannot be imported, raising "ModuleNotFoundError".

   Make sure that Tkwant is correctly build, see 
   :ref:`install`. 
   If Tkwant can be imported inside
   the Tkwant repository folder but not outside, the package is very likely not in the
   Python search path. If a symbolic link has been created, make sure that it
   points to the correct destination and that its origin is in the Python search path.

.. specialnote:: The simulation stops unexpectedly or with an incomprehensible error message.

   Enable :ref:`logging` to see possible warning messages.

.. specialnote:: The simulation stops with "IndexError" or the result has the wrong shape.

   No open modes are below the Fermi energy (chemical potential :math:`\mu` at :math:`T = 0`).
   By default, the Fermi energy is assumed to be zero. Plot the lead spectrum as in
   the first example in :ref:`getting_started` to check that open modes
   are below the Fermi energy.

.. specialnote:: The result saved to a file is empty when using MPI.

   Only the MPI root rank carries the simulation result, all other ranks have ``None`` as result. 
   Use the ``am_master()`` strategy from :ref:`mpi` to save the result
   from the root rank only.

.. specialnote:: Doing basic arithmetic operations with the result using MPI raises the error: "TypeError: unsupported operand type(s) for 'NoneType'"

   On all non-root MPI rank the result is ``None``, preventing arithmitic 
   operations like :math:`+, -` and :math:`*` on these ranks.
   Perform arithmetic operations only on the output from the MPI root rank
   by using the ``am_master()`` strategy from :ref:`mpi`.

.. specialnote:: Running Tkwant on a multi-core machine as a cluster fails.

   The number of OMP threads must be one. Set ``export OMP_NUM_THREADS=1``.

.. specialnote:: The simulation takes unexpectedly long.

   When the manybody integrand has a complicated structure 
   (for systems having resonances, strong perturbations etc.) the
   adaptive refinement does not make progress. One should first enable :ref:`logging`
   to check whether the simulation is indeed traped in the refinement cycle.
   If this is really the case, one can try to change the accuracy of the refinement
   process and also limit the total number of cycles. Alternatively, one might
   run the manybody simulation with the "low-level" approach using
   a fixed number of onebody states, see :ref:`manybody`.

.. specialnote:: The result seems to have numerical artifacts.

   Very likely, the manybody integral is poorly approximated.
   For the adaptive solver, check the estimated error and apply adaptive refinement.
   For the "low-level" approach, increase the number of integral splits, see :ref:`manybody`.

.. specialnote:: A tutorial example is not working.

   Update Tkwant and the required packages. Almost all tutorial examples execute real code to
   generate the output.



