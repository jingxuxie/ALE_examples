# Transport API, version 1

Run `python solve.py --input request.json --output response.json`. A request has `{"version": 1, "cases": [...]}`. Return `{"version": 1, "results": {CASE_ID: RESULT}}`. Process each case independently. Arrays are JSON lists of finite real numbers; use double precision. Every `id` is a unique string.

## Flow case

Fields: `kind="flow"`, `id`, `direction` (`"forward"` or `"inverse"`), `x` (length `dimension`), `log_density` (scalar), `times=[t_start,t_end]`, `parameters` (length `4 + dimension//2 + 1`), `cotangent` (same shape as `x`), `density_weight` (scalar), and `steps` (positive integer accuracy hint). Dimension is at least 3. The first four parameters are `a,b,c,d`; the remaining values are real logarithms of one-dimensional rFFT scale factors. Signed durations, shifted intervals, and zero duration are valid. Time magnitudes are at most 8; coordinate and parameter magnitudes are at most 3. Steps may be increased; there is no requirement to preserve a particular discrete integrator.

The forward map first applies `irfft(exp(log_scales) * rfft(x), n=dimension)`, then integrates the physical-time ODE

`dx_i/dt = a*x_i + b*tanh(x_i) + c*sin(t) + d*x_(i-1 mod dimension)`.

Log density is carried through the spectral change of variables and the continuous flow. Its time derivative is minus the divergence of this vector field. The inverse map reverses the entire composition on the independently supplied `x`; it is not a request to invert a forward output computed in the same case. `times` always describes the forward interval, including when its signed duration is negative.

Return `state`, `log_density`, `objective`, `time_gradient` (length 2), `parameter_gradient` (same length as `parameters`), and `input_gradient` (same length as `x`). The differentiated scalar objective is `dot(cotangent, state) + density_weight * output_log_density`. Differentiate with respect to both times, every parameter including all log scales, and the supplied input coordinates. The input `log_density`, cotangent, and density weight are held constant. Derivatives refer to the continuous map, to numerical accuracy, not an arbitrarily coarse step discretization.

## Acceptance case

Fields: `kind="acceptance"`, `id`, `times`, `parameters`, `steps`, `latents` (a list of vectors with common dimension at least 3), and `uniforms` (one fewer number than latent vectors, strictly between zero and one). Use the forward composition on each latent with the standard-normal log density `-0.5*sum(z*z) - dimension/2*log(2*pi)`. This defines each proposal state and its proposal log density. The unnormalized target log density is `-sum(0.25*x**4 + 0.3*x**2)`.

The transformed first latent is the initial retained state. Visit the remaining proposals in order. For each, compute `log_alpha = min(0, (target_new - proposal_new) - (target_retained - proposal_retained))`. Accept exactly when `log(uniform) < log_alpha`. On rejection retain the previous state and both of its densities. There are no derivatives of the discrete accept/reject decision in this API.

Return `proposal_states`, `proposal_log_density`, `log_acceptance`, `accepted` (0 or 1 per proposal after the initial state), and `retained_states` (including the initial retained state). The input specifies all randomness. A constant proposal-density offset can cancel in acceptance ratios; it does not excuse incorrect absolute densities.

## Execution

The evaluator invokes one process for a request containing several cases. Produce JSON only in the requested output file; diagnostics may go to stderr. On an individual case failure, return `{"error": "..."}` for that case rather than omit other cases. Use CPU and at most four threads. The public example contains no expected answers; evaluation requests are not a labeled training dataset. The runtime provides Python 3.12, NumPy, JAX 0.8.1, Flax 0.12.1, Diffrax 0.7.0, and Chex. No package installation or internet access is necessary.
