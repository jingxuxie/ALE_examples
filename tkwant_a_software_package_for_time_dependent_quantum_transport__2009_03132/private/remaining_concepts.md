# Remaining-concept decision after empirical screening

The selected release-qualification task is rejected under the >=0.90 rule. The fresh solver generalizes across all six families; no additional cases, tighter tolerances or output requirements are added. There is no fundamental redesign.

The reserve absorbing-boundary concept was re-inspected against the mandatory gates, including the actual v1.0.0 `leads.py` implementation:

- `_high_energy_reflect` and `_low_energy_reflect` provide the monomial reflection estimates.
- `_optimal_split`, at line 1252, is an explicit algebraic buffer/absorber fraction.
- `_optimize_length` and `_optimize_strength`, at lines 1689 and 1755, reduce the parameter selection to scalar searches using the supplied estimates.
- `automatic_boundary`, at line 1981, already connects band information and boundary construction.
- The documented truncated-energy-window limitation concerns extrema selection. Repairing it in isolation is ordinary numerical implementation, not a new professional research workflow.

A standalone task about these routines would collapse to visible formula translation, interpolation and scalar optimization. Including the complete official routines would expose nearly the entire solution. Removing them would turn the task into implementing an established algorithm. Expanding it to wavepacket and many-body validation would repeat the already screened workflow rather than create a genuinely different concept. In fact, without any private information, the fresh participant independently implemented a quartic absorber and compared it to a long hard-wall embedding on a fast-lead, long-horizon stress case at sub-1e-6 discrepancy.

Therefore the reserve fails the mandatory standard-shortcut/no-solution-oracle gates before construction. It is recorded as rejected, not represented as a built or empirically screened second pilot. Building an intentionally gate-failing second pilot merely to increment a counter would contradict the governing instruction to aggressively reject weak concepts.

The other three source-derived concepts were already rejected in `candidates.md`: the cavity reproduction and graphene visualization are clone/run or conventional propagation workflows; the isolated band-continuation concept is standard assignment and interpolation and lacks ownership of the full scientific workflow. Adding unrelated inverse inference, additional labels, adversarial formatting, or harder physical models outside the paper's central workflow is not used to manufacture hardness.

Five concepts were considered, one gate-passing concept was built and empirically screened, and no frontier-hard task is retained. This is a paper-level rejection, not a claim that every possible future task derived from this paper has been proven easy.
