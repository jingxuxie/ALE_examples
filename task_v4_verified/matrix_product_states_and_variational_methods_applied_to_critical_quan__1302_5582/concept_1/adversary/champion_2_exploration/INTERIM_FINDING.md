# Confirmed private in-domain residual gap

All twelve initial requests have valid v4 outputs. No larger-domain requests,
new generation, or frozen evaluator invocation occurred.

The retained candidate is `requests/disordered_weaklink_cap12_odd.json`:
N=64, d=14, bond cap=12, odd parity, omega=0.55, lambda4=0.05,
spatially disordered mass and springs, and three springs equal to 0.05.
Every coefficient and size lies in the advertised contract.

Trusted energies:

- `runs/disordered_weaklink_cap12_odd/v4_40/state.npz`: 40.22967442107043.
- `runs/disordered_weaklink_cap12_odd/repeat_v4_40/state.npz`: 40.22967442107043.
- `runs/disordered_weaklink_cap12_odd/v4_120/state.npz`: 40.22967442107043.
- `runs/disordered_weaklink_cap12_odd/v3_40/state.npz`: 40.22964675350228.
- `runs/disordered_weaklink_cap12_odd/teacher_90/state.npz`: 40.22964675350199.

The teacher_90 state is a warm refinement of the v3 seed by the independently
implemented corrected two-site/one-site engine. The corresponding teacher_120
run from the v4 seed retains its higher local minimum, 40.229674421070364.
These are attained same-cap energies, not certified ground energies.

The gap is approximately 2.76676e-5 total, 4.32306e-7/site, or 4.32306 times
the 1e-7/site screen. Both repeated v4 runs and the 120-second-budget v4 run
exit after approximately 16 CPU seconds; this is not timeout invalidity.
Every listed state passes trusted cap, archive, norm, and odd-parity checks.

The two branches differ in virtual charge allocation only at cuts 3 and 4:
v4 has seven even/five odd states, whereas v3 has six even/six odd. This is
a measured association, not yet a causal diagnosis. Allocation profiles and
trusted local observables are in the candidate's `allocation_diagnostics.json`.

Other completed candidates are below screen. The same disordered Hamiltonian
at cap 24 has only a 1.30280e-8/site v4-v3 difference. This is one narrow
in-domain failure cluster, not evidence of a calibrated worst-family deficit.
