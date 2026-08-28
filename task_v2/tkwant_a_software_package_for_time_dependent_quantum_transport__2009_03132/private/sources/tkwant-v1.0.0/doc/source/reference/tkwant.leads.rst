:mod:`tkwant.leads` -- Time dependence and boundary conditions for leads
========================================================================

.. module:: tkwant.leads

Adding time-dependence
----------------------

.. autosummary::
    :toctree: generated/

    add_voltage


Boundary conditions
-------------------
Boundary conditions for systems with leads attached; used with
the solvers in `tkwant.onebody.solver`.

.. autosummary::
    :toctree: generated/

    SimpleBoundary
    MonomialAbsorbingBoundary
    GenericAbsorbingBoundary
    automatic_boundary


Analyse lead reflection
-----------------------

.. autosummary::
    :toctree: generated/

    AbsorbingReflectionSolver
    AnalyzeReflection
    AnalyzeReflectionMonomial
