# NPZ contract (version 1)

Load/save ordinary NumPy `.npz` archives with `allow_pickle=False`. Keys are
literal, case-sensitive names. No object arrays, JSON strings, or extra output
axis conventions are used. Extra output keys are ignored. All real-valued
outputs must be real arrays; `unpacked_rfft` is complex. Boolean masks may be
Boolean or numerical 0/1. Scalar means shape `()`, not `(1,)`.

## Shapes and inputs

Let `S = tuple(spatial_shape)`, `C = tuple(channel_shape)`, and
`B = tuple(batch_shape)`. These three keys are 1D int64 arrays; empty channel
or batch shapes are allowed. Let `d=len(S)`, `V=prod(S)`,
`R=S[:-1]+(S[-1]//2+1,)`, `H=prod(C)` (1 if empty), and `F=prod(B)*V*H`.
Arrays use C ordering. Only the `d` spatial axes after the batch axes are
transformed; channel axes are never Fourier-transformed.

| Input key | dtype and shape | Meaning |
| --- | --- | --- |
| `spatial_shape`, `channel_shape`, `batch_shape` | int64 vectors | Shapes above |
| `x`, `direction_x`, `cotangent` | float64, `B+S+C` | Field, input direction, objective coefficient |
| `q` | float64, `B+(V,)+C` | Independently supplied packed coordinates to decode; not the encoding of `x` |
| `log_density`, `direction_log_density` | float64, `B` | Initial per-event density and its direction |
| `theta`, `direction_theta` | float64, `(P,)` | Parameters and parameter direction; `1<=P<=6` |
| `base` | complex128, `T` | Nonzero base spectrum |
| `amplitude`, `phase` | float64, `(P,)+T` | Log-amplitude and phase features |
| `probes` | complex128, `(K,)+T` | Spectra whose symmetry violations must be measured |

Here `T` is either `R` (shared across **every** channel) or `R+C`
(per-channel). No leading batch axes occur in spectra. Determine the layout
from `base.ndim`; do not confuse a spatial axis with a channel axis.
`K` is the number of probes, not a fixed constant.

## Independent real representation

For an index tuple `k` in the reduced grid `R`, define its conjugate partner
`kc=tuple((-k[a]) % S[a] for a in range(d))`. It is stored iff
`kc[-1] < R[-1]`. Tuple comparison below is ordinary lexicographic order.

`mr[k]` is true except when the partner is stored and `k > kc`.
`mi[k]` is true iff `mr[k]` is true and `k != kc`.
Thus `sum(mr)+sum(mi)=V`. These masks have shape `R`, without batches/channels.

Compute `X=rfftn(x, s=S, axes=spatial_axes, norm="ortho")`.
For each batch/channel separately, `packed` is the concatenation of:

1. `Re(X[k])` for `mr[k]`, in C-order traversal of `R`;
2. `Im(X[k])` for `mi[k]`, in that same order.

There is **no sqrt(2) rescaling**, interleaving, or additional density output
for this representation conversion. The packed axis replaces all spatial
axes; channels remain trailing. `packed` has shape `B+(V,)+C`.

Decode the independently given `q` with the exact inverse convention. Populate
real parts at `mr`, imaginary parts at `mi`, zero imaginary parts at self modes,
and set every non-independent stored coefficient to its partner's conjugate.
Return this as `unpacked_rfft` of shape `B+R+C`, and its
`irfftn(..., s=S, axes=spatial_axes, norm="ortho")` as `unpacked` of shape
`B+S+C`. Always pass the original spatial shape, including odd last lengths.

## Symmetry diagnostics

Return `mr` and `mi`. Also return `asymmetry`, shape `(K,)`. For each probe
`s`, it is the maximum of:

- `abs(s[k] - conj(s[kc]))` over stored conjugate pairs and all channels;
- `abs(Im(s[k]))` over self-conjugate modes and all channels.

An empty maximum is zero. Interior reduced-grid modes with an unstored
partner impose no constraint. This diagnostic does **not** project, reject,
or test invertibility of a probe; zero spectra have zero symmetry violation.
Probes may be valid or invalid and do not define the transport below.

## Spectrum, transport, and density

For the supplied parameter vector define

```
s(theta) = base * exp(sum_p theta[p]*amplitude[p]
                     + 1j*sum_p theta[p]*phase[p])
```

Inputs guarantee that this spectrum is nonzero and conjugate-consistent for
every real `theta`: `base` is real at self modes, amplitude features agree at
stored partners, phase features change sign there and vanish at self modes.
Self-mode base values can be negative. Non-self modes can have complex phases.

Return `y=irfftn(s*rfftn(x))` and `reverse_y=irfftn(rfftn(x)/s)` with explicit
`s=S`, the spatial axes, and `norm="ortho"` in **both** FFT directions.
Reverse is applied to the supplied `x`, NOT to `y`. Both have shape `B+S+C`.
Broadcast a shared spectrum by appending `len(C)` singleton dimensions.

Let `D(theta)` be the real-dimensional log absolute determinant of the forward
linear map on one entire event `S+C` (not on the batch). Return
`log_density_y=log_density-D` and `reverse_log_density=log_density+D`, shape `B`.
The determinant counts independent real degrees of freedom, including all
channels; its absolute value handles negative real factors. Do not count batch
members as additional event dimensions. No probability normalization is added.

## Sensitivities

All derivative outputs concern the **forward** map. Return:

- `jvp_y`, shape `B+S+C`: derivative of `y(x+t*direction_x,
  theta+t*direction_theta)` at `t=0`.
- `jvp_log_density`, shape `B`: derivative of
  `log_density_y(x+t*direction_x, theta+t*direction_theta,
  log_density+t*direction_log_density)` at `t=0`.
- `grad_x`, shape `B+S+C`, and `grad_theta`, shape `(P,)`: ordinary real
  gradients of the scalar
  `J = sum(cotangent*y)/sqrt(F) + mean(log_density_y)/(V*H)`.

Hold every input except the differentiated argument fixed in the gradients.
Complex spectra are intermediate representations of a real-to-real map;
these are not unconstrained complex derivatives or elementwise derivatives.

## Momentum and shell outputs

Return `momenta` and `lattice_momenta`, shape `R+(d,)`. For each axis of length
`L`, grid index `n` has signed integer `m=n` when `2*n<=L` and `m=n-L`
otherwise. `momenta[...,a]=2*pi*m/L`; `lattice_momenta=2*sin(momenta/2)`.
In particular an even Nyquist coordinate is **+pi**, not -pi. Lattice spacing
is one. Return `shell_squared`, int-valued shape `R`, equal to `sum_a m[a]**2`.
This integer shell index is distinct from physical momentum squared on
rectangular lattices. No folding of the storage indices themselves is implied.

## Evaluation scope and execution

Evaluation covers mixed-parity 2D/3D lattices, batches, shared/per-channel
spectra, multiple channel axes, and 64×64/128×128 fields. Use float64/complex128
precision. Spectral arrays are supplied numerical inputs, not hidden
parameters: every archive contains `base`, `amplitude`, `phase`, `theta`, and
the stated directions. Their values and geometry vary, but all nonzero and
symmetry preconditions above hold. Only `probes` may violate those symmetry
conditions. No unpublished spectral formula or fitted coefficients are needed.

Each invocation has a four-core CPU affinity cap, at most four numerical-library
threads, and 60 seconds including sandbox startup and file I/O. A tighter
inherited CPU allocation is preserved. Dense spatial Jacobians are unnecessary.
Execution is network-isolated: public files appear read-only at `/task`, the
submission at `/submission`, and the current input/output directory is writable
at `/work`. The interpreter is `/task/input/runtime/bin/python3.12`; the command
is `/submission/solve.py /work/input.npz /work/output.npz`. Temporary storage is
available at `/tmp`. Private cases other than the current input, reference
outputs, and source implementations are not accessible. Imports may use
`/submission` and `/task/workspace`; do not depend on the host filesystem or
environment.

## Metric

For each required array, error is the mean of (i) RMS absolute difference
divided by `max(1,RMS(reference))` and (ii) maximum absolute difference divided
by `max(1,max(abs(reference)))`. The max term prevents a single broken plane
or self mode from disappearing in a large lattice. Average array errors within
each case/family, then equally across cases.

Family keys: packing=`packed`; unpacking=`unpacked,unpacked_rfft`;
symmetry=`mr,mi,asymmetry`; transport=`y,reverse_y`;
density=`log_density_y,reverse_log_density`;
sensitivity=`jvp_y,jvp_log_density,grad_x,grad_theta`;
momenta=`momenta,lattice_momenta,shell_squared`.

For family error `E`, stored weak error `W>0`, official error `0`, and
`tau=1e-10`, define `skill=1-log1p(E/tau)/log1p(W/tau)` and
`score=1/(1+exp(log(9)-(log(9)+log(19))*skill))`. Skill is not clipped;
scores have no correctness threshold. A missing/invalid array receives array
error `1e6`; a failed or timed-out invocation receives that error for every key.
Wall times and execution failures are also reported. Time is not a separate
accuracy family; the 60-second cap enforces the scalable execution envelope.
The final score is the unweighted mean of the seven family scores. The official
zero-error anchor has score 0.95 and skill 1; the weak anchor has score 0.10 and
skill 0. Skills remain unclipped, including for worse-than-weak submissions.
