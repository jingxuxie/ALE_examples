# Resource-contract adapter

The unmodified fresh champion is archived in `../../champions/generation_2/`.
It is designed for exactly three requests: two initial settings and a final
adaptive setting. The prospective two-request audit changes one line to truncate
the initial-setting list to `query_budget - 1`. No inference, fitting, final
experiment selection, initialization, parameter values, or evaluation targets
change. The adapter behaves identically to the champion at the original budget
of three. This avoids treating a trivial excess-query protocol violation as a
scientific counterexample: the audit scores the actual accuracy of a valid
budget-adapted incumbent.
