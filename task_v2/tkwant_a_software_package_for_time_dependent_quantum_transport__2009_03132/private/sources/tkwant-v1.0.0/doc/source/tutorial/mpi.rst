.. _mpi:

Parallelization with MPI
========================

Particularly with larger simulation times and system sizes,
complex calculations are computationally intensive.
In order to keep the actual simulation time manageable,
tkwant is parallelized with the Message Passing Interface (MPI).
With MPI, tkwant can run it in parallel, e.g. on the local computer or on a cluster.

Parallel programming and in particular MPI is a vast subjet
and the following tutorial cannot explain these techniques here, but we refer
to dedicated material which can be found in the web.
This tutorial will explain however the very basic concept which is sufficient to run tkwant
simulations in parallel without having a deeper knowledge in MPI.
This is possible since compute-intensive routines are natively MPI parallelized in tkwant, 
such that only minor changes to a simulation script are required.
We will explain them in the following.


Running code in parallel with MPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As an example, let us focus on the tkwant example script
:download:`fabry_perot.py <fabry_perot.py>`.
To execute this script on 8 cores, the scripts
must be called with the following command:

::

    mpirun -n 8 python3 fabry_perot.py

Calling the script with:

::

    python3 fabry_perot.py


will run it in standard serial mode.

Enabling output only from the MPI root rank
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running a script with the prefix ``mpirun -n x`` will execute the entire
script *x* times. While tkwant is designed to benefit from this parallelization,
any output in the script as printing, plotting or writing to a file
will be also repeated  *x* times. This is unpractical, as e.g. a ``print()`` call in the simulation
script will print some information *x* times instead of only once.
Moreover, not all of the *x* parallel runs are equivalent, 
but the result of a calculations from the tkwant solvers is returned
by default only on one MPI rank, the so-called master or root rank, which has the rank index 0.
It is sufficient however to add a few additional lines of code, in order to
redirect all plotting and printing to the MPI root rank, such that both serial and parallel execution
will lead to the same result.

As an example, we look again at the script
:download:`fabry_perot.py <fabry_perot.py>`.
In this script, a few additional lines of code
redirect all plotting and printing to the MPI root rank.
For plotting and saving the result, the following block of code can be used:

.. jupyter-execute::

    import tkwant

    comm = tkwant.mpi.get_communicator()
    def am_master():
        return comm.rank == 0

    # do the actual tkwant calculation

    if am_master():
        # plot or save result
        pass

Quite similar, printing a message only by the master rank is possible by
the following lines of code:

.. jupyter-execute::

    import sys

    def print_master(*args, **kwargs):
        if am_master():
            print(*args, **kwargs)
        sys.stdout.flush()

    print_master('this message is printed only by the master rank')

Note the flush command to prevent buffering of the messages.


MPI communicator
~~~~~~~~~~~~~~~~

The following information is not relevant for tkwant users, but inteded for
tkwant developers working with MPI.
Tkwant initializes automatically the MPI communicator, if needed.
To uses MPI, the function ``mpi.get_communicator()`` returns tkwant's global
MPI communicator which is used by all routines by default:

.. jupyter-execute::

    import tkwant

    comm = tkwant.mpi.get_communicator()
    print('rank={}, size={}'.format(comm.rank, comm.size))


``comm`` is basically a copy of the MPI ``COMM_WORLD`` communicator.

If tkwant should be used as an external library with a different MPI communicator,
the routine ``mpi.communicator_init()`` allows to change the default
communicator:

.. jupyter-execute::

    import tkwant
    from mpi4py import MPI

    my_comm = MPI.COMM_WORLD
    tkwant.mpi.communicator_init(my_comm)

Note that the MPI communicator must be set *after* importing the tkwant module and
*before* executing any tkwant code.


Multi-threading
~~~~~~~~~~~~~~~

Tkwant does not support multi-threading as OpenMP. The environment variable
``OMP_NUM_THREADS`` must be set to one:

::

    export OMP_NUM_THREADS=1


Examples
~~~~~~~~

The example scripts
:download:`fabry_perot.py <fabry_perot.py>` and
:download:`voltage_raise.py <../../examples/voltage_raise.py>`
can both be executed in parallel using MPI.


References
----------

`MPI standard documentation
<https://www.mpi-forum.org/>`__

`MPI for Python
<https://mpi4py.readthedocs.io/en/stable/>`__

