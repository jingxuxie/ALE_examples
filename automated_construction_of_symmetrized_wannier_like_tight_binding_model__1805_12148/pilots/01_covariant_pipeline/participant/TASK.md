# Covariant tight-binding pipeline

Repair and integrate the supplied historical TBmodels routines so that a
Wannier90 import and an independent change of unit cell preserve the requested
orbital gauge. The workspace contains working historical implementations with
real defects, not empty stubs. You may modify or replace them.

For each case, import the complete hopping model, respect the Cartesian centres
and Wigner–Seitz corrections, select the requested centre assignment, and form
the specified physical supercell. Separately, transport the supplied dense model
to its requested cell and origin. Return positions, full complex Hamiltonians in
both Bloch conventions, and bands in the specified orbital order.

Run `python attempt/solve.py --input CASE --output RESULT.npz`, where `CASE` is a
case directory. Copy `participant/workspace/` into your writable `attempt/` to
start. The initial entrypoint runs the unrepaired historical pipeline.

The technical contract is in `workspace/SCHEMA.md`. One unlabeled smoke case is
in `input/smoke/`; `workspace/smoke_check.py` checks only internal invariants.
Evaluation uses unseen full material models and transformations. Import and
geometric transport receive separate continuous credit. Correct band energies
alone do not establish a correct orbital gauge. Do not depend on private files,
network access, or an installed modern TBmodels package.
