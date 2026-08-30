# Wide-frontier scheduling ratchet

Generation 1 was solved by a fresh ultima-alpha agent: core gain 2.4014621856,
worst-family gain 1.4880608806, with all dependency and peak checks passing.
The complete submission is `champions/generation_1/`; the old task and evaluator
are archived under `generations/generation_1/`.

We ran that champion's own unchanged 1,000-start seeding script and native
optimizer over 24 private graphs spanning modular, wavefront, reconvergent and
heterogeneous families, with two graph sizes per family. Each champion solve
received 60 seconds. All orders were independently checked. A 120-second
additional seed continuation exposed the largest gaps on three 1,600-node wide
wavefront cases: gains 1.05018861, 1.02517321 and 1.13589325 over the already
optimized champion. A second expensive continuation continues separately and
does not alter the frozen ratchet target.

The observed failure cluster is wide live-register frontiers: the meaningful
improvements reduce peak occupancy, not merely tiny qubit-time tie breaks.
Most other workload families show only small residual changes. We therefore
focus on the three measured wide-frontier failures rather than adding unrelated
files, arbitrary hidden trivia, or numerically oversized integers.

Generation 2 supplies those graphs and the champion's precomputed schedules as
its runnable baseline. The fixed target is 1.06 geometric-mean gain and at least
1.02 gain for every individual graph, with the original 5% peak-regression guard.
The private first continuation already supplies an exact passing artifact, so
achievability is established independently of any fresh attempt. Search outputs
are not canonical reference answers; any legal schedules reaching the disclosed
resource targets pass.

Only the new participant tree is exposed to the new fresh agent. The prior
champion optimizer/source, private generators, challenge search, earlier
attempts and passing continuation artifact remain excluded. Baseline schedules
are provided task assets; no hidden answer is needed by the evaluator.
