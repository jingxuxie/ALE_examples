# Physical and data contract

All quantities are dimensionless oscillator units: mass and hbar are one; time
is inverse reference trap frequency. The state is normalized to integral |psi|²=1.
The prescribed real-time, scalar, conservative rotating-frame equation is

    i dpsi/dt = [-1/2 laplacian + V(x,y,t) + g |psi|² - omega Lz] psi
    Lz = -i (x d/dy - y d/dx).

There is no phenomenological damping, imaginary-time relaxation, renormalization,
or density filtering during the requested evolution. Initial preparation is
already complete. Nonzero current, core depletion, and defects can coexist with
a time-dependent density: do not impose an equilibrium ansatz after an imprint.

NPZ arrays: `x[nx]`, `y[ny]` are strictly increasing uniformly spaced *physical*
coordinates; `psi[ny,nx]` is complex128; `potential[ny,nx]` is the static trap;
`roi[ny,nx]` is a nonnegative integer domain label; `bulk[ny,nx]` is a boolean
measurement mask inside positive ROI. Grids are periodic numerical boxes with
negligible initial density at the box boundary, not periodized vortex lattices.
Use ordinary (not toroidal) spatial geometry for the ROI analysis. Coordinates,
cell areas and rectangular grids must be respected. Do not change output grids.

Each manifest case has `id`, relative `asset`, `g`, `omega`, ascending `times`
starting at zero, `imprints`, `correlation_edges`, `spectrum_edges`, and optionally
`drive`, `intervention_center`. Names carry no physical semantics.
At t=0 apply every imprint `{x,y,charge}` simultaneously as multiplication by
exp(i * charge * atan2(y-y0,x-x0)). `charge` is a signed integer increment, not the
desired final circulation. The first saved frame is *after* the intervention;
later frames are the same state's conservative evolution. Do not fill the core
by editing the density. Never overwrite the initial assets.

When present, the drive adds

    amplitude * sin(frequency*t)^2 * exp(-[(x-center[0]-travel*sin(frequency*t))²
                                          +(y-center[1])²]/(2*width²))

to the static potential. All other coefficients are constant. Static energy is
conserved only for undriven cases; normalization is conserved in all cases.

## Required measurements and conventions

`<case>.npz`: `psi[nframes,ny,nx]`, `times[nframes]` matching the manifest.
`<case>.json`: one object per frame with `cores`, `topology`, and `physics`.

**Cores**: list `[x,y,signed_charge]` for all singly quantized positive or negative
phase singularities inside positive ROI. Subgrid positions are required. Density
minima alone are not vortices. ROI/bulk membership is evaluated at the nearest
grid sample, rounding to nearest; all positions use the original physical axes.
Negligible numerical noise outside the ROI is not a core. There are no multiply
quantized cores within the measurement ROI in the acceptance data.

**Topology**: coordination and sixfold bond order concern *positive* vortices.
Build neighborhoods using all positive cores within each positive ROI label,
but count and correlate only bulk cores. A Delaunay edge is admissible only if
its entire segment stays within that label (checking samples no farther than
half the smaller grid spacing apart suffices). Different labels never share
edges. Holes and gaps are not material. Boundary guard cores contribute neighbors
even when they themselves are excluded from bulk statistics.

For a positive core, local sixfold order is the arithmetic mean of exp(6 i theta)
over its distinct admissible neighbors; zero if there are no neighbors. Correlation
is the real part of local order at the first core times the *complex conjugate*
at the second, averaged over unordered, distinct bulk-core pairs whose Euclidean
separation lies in a given half-open radial bin. All bulk pairs are counted, even
when their two local neighborhoods are in different domains. Empty bins contain
zero and a zero pair count. Do not replace a pair correlation by local magnitude.
Output `counts[13]` for coordination 0 through 12, `correlations`, `pair_counts`,
and `defect_radius`. The last is RMS distance of bulk positive non-sixfold cores
from `intervention_center` (default [0,0]); zero when none exist. Edges outside
the material and mesh-boundary artifacts must not masquerade as bulk defects.

**Physics**: `norm`, `r2` (unnormalized integral r² |psi|²), and rotating-frame
`energy` (kinetic + trap + g |psi|⁴/2 - omega times angular momentum density).
The requested kinetic decomposition uses the *lab-frame*, density-weighted
velocity u = Im(conj(psi) grad psi)/|psi|, zero at exact vacuum; it is not the
gradient of an independently unwrapped global phase and does not subtract the
rigid rotation. Split u into longitudinal (curl-free) and transverse
(divergence-free) Fourier components on the numerical box. Assign the k=0
component to the transverse part. `Ec` and `Ei` are their integrated half squared
norms using the physical cell area. `Eq` is integral |grad |psi||²/2. Spectral
derivatives on the given periodic grid define the measurement convention.
`Ec_bins`, `Ei_bins` are *shell sums* of the corresponding energies with radial
boundaries `spectrum_edges`, not shell averages, not additional factors of k,
and not one-dimensional projections. With unnormalized forward FFT, each mode's
weight is cell_area/(2*nx*ny). These units and normalization are observable
definitions, not an integrator prescription. Avoid dividing floating-point
vacuum by zero; the numerical-vacuum convention is density <= 1e-12 times the
frame's maximum density. At that cutoff u is zero.

`results.csv` columns are shown in the writer. `nplus,nminus` count signed cores
inside bulk; `n5,n6,n7` are bulk positive coordination counts; `g6_near,g6_far`
are the first/last correlation bins. `scaling.csv` contains one row per case
with nx,ny,dt (or representative max timestep),frames,wall_seconds,max_rss_kib.
Use finite numeric values throughout. Norms and energies are not divided by
the observed instantaneous norm to hide drift.
