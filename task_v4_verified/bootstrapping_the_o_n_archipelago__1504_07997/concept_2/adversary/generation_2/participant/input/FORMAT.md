# Sparse mixed-OPE certificate format

Construct a parsimonious, OPE-consistent spectral completion for eight mixed
correlator data sets. The supplied finite radial/partial-wave model isolates
the shared positive-matrix structure of the O(N) mixed-correlator bootstrap;
it is not a full conformal-block or crossing-symmetry calculation.

Assets: `input/instances.json`, a runnable `baseline/solve.py`, and
`workspace/check.py`. Each instance supplies candidate dimensions/spins,
the already evaluated kernel `design[row][candidate]`, and observations
`target[row][component]`. Components are `(phi_phi, phi_s, s_s)`.

Submit `answer.json` in your output directory, with schema
`{"cases": [{"id": "...", "atoms": [{"index": 0, "ope": [0.7, -0.2]}]}]}`.
For each atom the real OPE vector `(a,b)` contributes
`design[:,index] * (a*a, a*b, b*b)`. Use at most `max_atoms` distinct indices.
Index zero must occur and its first squared coefficient must equal
`shared_ope_squared`; this is the coefficient shared with an external-vector
channel. The sum of all squared OPE coefficients cannot exceed `trace_budget`.
Every coefficient must have absolute value at most 4.

The certificate condition is maximum absolute componentwise residual,
divided by `scales[row][component]`, at most `2e-8`; shared-coefficient error
at most `2e-10`; and trace budget slack at most `2e-10`. All arrays must be
finite. No coefficient rounding or truncation is performed by the checker.

The objective is a valid certificate for **every** instance. Partial credit
is the fraction of valid instances; the worst-family fraction is also
reported. Any admissible completion earns credit, not just the planted one.
The checker makes no reference-solution comparison.

Run the baseline with `python baseline/solve.py input/instances.json answer.json`.
Check with `python workspace/check.py input/instances.json answer.json`.
The baseline accepts `--seconds-per-case 300` (its default). Scratch state is
created beside the output file; input and baseline directories may be read-only.
You have one hour, up to four CPU threads and 4 GiB RAM. Use the installed
Python, NumPy, SciPy and mpmath; no network or privileged files. The final
artifact is data, so no submission code is run during grading.

Each instance has 96 candidate columns and 40 probes. Candidate metadata records
`dimension`, `spin`, and `column_scale`; probes record `t`, `eta`, and `order`.
The supplied design is the normalized leading-radial/Legendre surrogate
`exp(-t*dimension) * P_spin(eta) * (dimension/8)^order / column_scale`.
The numerical arrays define the certificate problem. Candidate indices carry
no implicit spin or support information. IDs are opaque labels.
