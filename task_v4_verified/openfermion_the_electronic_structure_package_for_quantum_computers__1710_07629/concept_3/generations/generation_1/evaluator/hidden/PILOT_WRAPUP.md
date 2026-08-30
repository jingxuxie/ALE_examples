# Bounded pilot and lineage

The eight-case L12 pilot used the same four physical family laws, two cases per
family, and independently generated double-precision source labels. Its initial
snapshot has no fixed-size buffer limitation: no dimension adaptation was made.

During concurrent private label generation the snapshot's L12 CLI exceeded
25 seconds. That timing is not the uncontended result. A repeat after source
jobs ended completed eight L12 cases in 14.727756 CPU / 15.097225 wall seconds,
with errors around one micro-hopping-unit. Eight L10 controls completed in
1.321496 CPU / 1.683667 wall seconds. Per-row steady-state CPU sums were
15.122516515 and 0.820535389 seconds respectively, projecting about 255 CPU
seconds for a 256-case equal mixture, excluding one startup. This is measured
scaling evidence, not a universal lower bound or proof that learning will pass.

The promoted original champion changed `hubbard.cpp`, `hubbard.so`, and
`physics.py` after the snapshot; only `solver.py` stayed identical. The final
engine adds a symmetric neutral-sector optimization and changes convergence
defaults. `lineage.json` records both hashes. `participant/baseline_exact/`
contains the final champion verbatim, not the earlier pilot. Its new-generation
quality and full-batch resource reports supersede pilot projections for that
engine. The final champion passed the original 8/10-site task, not this ratchet.

Twelve sites increase the half-filled neutral sector to 853,776 dimensions
from 63,504 at ten sites. The bounded pilot justifies trying 10/12 without
escalating to fourteen sites. Targets were held at 0.03/0.02 overall and
0.05/0.035 per family, 25 seconds and one CPU, before any new fresh attempt.
Reference ncv=16 calibration agreed with two independently generated L12
references to below 3e-14 while taking about 22 CPU seconds per case alone;
parallel generation cost is measured separately because shared-memory traffic
substantially changes that timing.
