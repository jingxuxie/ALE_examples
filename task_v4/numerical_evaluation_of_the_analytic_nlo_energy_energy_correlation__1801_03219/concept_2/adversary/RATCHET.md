# Independent-rule ratchet

Both generation-one agents construct valid material counterexamples. Their
worst independently checked margins above the unchanged required error are
1.2501586 and 1.2918926. All three color moments pass, with frozen/native
agreement separately checked. The second witness is the champion because its
minimum margin is larger. Both witnesses and the old grader remain archived.

The failure cluster is correlated aliasing of the embedded Gauss/Kronrod and
parent/children discrepancies: several coarse leaves survive with tiny reported
error even though their actual integrals are wrong. This is not raw analytic
formula cancellation, and not a midpoint/bin mismatch.

Generation two preserves the kernel, parameter domain, Fourier cap, lattice,
reference gates and materiality threshold. It adds an independently sampled
Gauss-Legendre-12 estimate on each panel; its absolute discrepancy is an extra
floor on the local error. Returned values are still the genuinely computed
Kronrod integrals. No finer initial mesh is forced. The champion now scores
zero against the guarded method, and numerical tests on regular/oscillatory
functions and the native calibration still pass.

The old champion is included as the runnable current baseline. Two completely
fresh agents must defeat the strengthened method. Achievability of that new
condition is unknown until an independently validated witness passes. The
private multi-leaf search launched before this guard is generation-one evidence
only, not a generation-two solution.
