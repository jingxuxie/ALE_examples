# Privileged builder portfolio, never a fresh champion

These programs are NOT participant submissions or fresh attempts. Do not expose
this directory in a fresh allowlist. Mount only its `reference/` leaf for the
privileged checks. Reports are siblings of that leaf and remain invisible.

`reference/solution.py --policy static` is a passing latent-blind witness. Its
allocation is computed from public coefficients and midpoint log bounds; it
collects 40,000 shots, then fits only the observed syndrome histograms. It reads
no hidden files, latent rates, private episode identifiers, or sampling seeds.

`--policy robust` is also a passing witness: it updates estimates from pilot data
and minimizes a combination of average and worst-family predicted error, with a
stabilized Fisher estimate. All policies run under the same bubblewrap, API,
query/shot budget and CPU accounting as a submitted worker.

`adaptive_report.json` uses a five-batch refit cadence, preserved in the code;
`robust` and `minimax` use a four-batch cadence. The program defaults to the known
passing static policy. The independent true-rate Fisher oracle in the separate
science audit is NOT this program and is not passing-solution evidence.
