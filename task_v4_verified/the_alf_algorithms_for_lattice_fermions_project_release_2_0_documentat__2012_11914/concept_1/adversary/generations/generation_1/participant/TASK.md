# Audit a screened Hubbard simulation window

A simulation team provisionally treats a doped square-lattice Hubbard window
as sign-free after a short auxiliary-field screen. Find a reproducible physical
counterexample to that screening claim, not a floating-point sign error.

`input/model.json` fixes the simulation and certification neighborhood.
`input/CONTRACT.md` specifies the weight and artifact format. `workspace/physics.py`
provides a double-precision diagnostic; `baseline/search.py` is a runnable weak
search. These assets are not a guarantee that the claim is true or false.

Write `witness.json` in the supplied output directory. It must contain one legal
auxiliary-field configuration whose two-flavor fermion weight is strictly negative
at every specified certification point. The independent checker reproduces signs
at two arbitrary precisions and checks agreement. All model and artifact
constraints are public; there are no secret witness conditions.

The search budget is one hour, at most four CPU threads, and 4 GiB RAM. No network
or external artifacts. Scoring is the fraction of certification points with a
verified negative weight; passing requires all points. A valid-format but positive
configuration does not pass.
