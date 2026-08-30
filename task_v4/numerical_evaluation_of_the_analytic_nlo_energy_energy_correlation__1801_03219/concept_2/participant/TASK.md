# Falsify an NLO EEC integration error claim

Find a smooth, bounded signed angular-moment weight for which the supplied
frozen integrator reports convergence but materially understates its true
integration error in all three color contributions of the NLO EEC.

`input/` provides the stable calibrated kernel, fixed integrator, constraints,
and a local screening API. This generation adds a non-nested Gauss-12 guard to
the estimator after the earlier champion defeated its embedded and parent-child
checks. `baseline/champion.py` copies that champion witness to an output folder;
`baseline/search.py` is also available as a weak search.
The complete observable, JSON grammar and numerical contract are in
`input/SPECIFICATION.md`; these define the task, not a prescribed search method.

Write only a static `witness.json` in the requested output directory. It chooses
one allowed finite angular bin, a bounded twelve-frequency Fourier weight and
a positive broad detector response. The file must satisfy the exact integer,
bandwidth, norm and schema constraints. Submission code is never executed.

For every color contribution, certified lower error E must exceed
`max(20*tau, 50*reported_error, 1e-5*reference_L1)`, with convergence reported by
the frozen method. Independent refinement and source-agreement gates must also
pass: inaccurate integrand values and point-versus-bin substitutions do not
qualify. Scores measure the achieved fraction of this target, both averaged
and in the worst color family.

The construction budget is one hour; NumPy, SciPy and mpmath are available.
The local API gives screening feedback, not the private convergence references.
