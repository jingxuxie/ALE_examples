# Private evaluator

Never expose this directory, `adversary/`, `attempts/`, `champions/`, `status.json`,
or `provenance.md` in a participant workspace. The public export is exactly
`participant/`. Do not put paper text or downloaded source in that export.

Run from any working directory:

```
/usr/bin/python3 /absolute/path/to/concept_1/evaluator/evaluate.py --solution /absolute/path/to/solution.py --output report.json
```

The solution's parent directory is its read-only submission bundle. Do not use a
parent that contains private assets. Bubblewrap is mandatory; failure is an
infrastructure error, never permission to execute the submission unrestricted.
Only the bundle, current input/output scratch, system binaries/libraries, dynamic
linker cache and alternatives are mounted. User/PID/network/IPC namespaces are
unshared, capabilities dropped, environment cleared. One process, one numerical
thread, 8 CPU seconds, 1 GiB address space, 64 KiB result. A generous 180-second
wall watchdog is deliberately separate from the CPU score. The outer host must
permit bubblewrap user namespaces. No dependency installation is necessary.

## Objective and enclosure

The oracle does not import any submitted/baseline implementation. For nodes t_i,
it computes positive cardinal products in log space, not a cancellation-prone
barycentric quotient. It scales y=min(a)*x; constant prefactors cancel exactly.

On a node-free interval [L,R], let D_j=max(|L-t_j|,|R-t_j|),
P_i=prod_{j!=i}D_j, S_i=sum_{j!=i}1/D_j, H_i=sum_{j!=i}1/D_j^2,
V'=a+sum_p1/(L+p), V''=sum_p1/(L+p)^2 and
C_i=1/(mu(t_i)*prod_{j!=i}|t_i-t_j|). Absolute polynomial derivative bounds give

    |lambda''(x)| <= mu(L) sum_i C_i P_i [(V'+S_i)^2+V''-H_i] = M.

Consequently lambda(x)<=max(lambda(L),lambda(R))+M*(R-L)^2/8.
Adaptive best-first subdivision encloses every interval and every supplied
weight until the global relative gap is <=8e-5. This is not merely a grid or a
unimodality assumption: the curvature bound checks for peaks missed by sampling.
The initial partition includes zero, every node, and the tail endpoint.
Every absolute cardinal summand has log derivative at most
-a+degree/(x-max_node), minus nonnegative pole contributions. Beyond
max_node+(2*degree+4)/min(a) the entire tail decreases at rate at least min(a)/2.
The endpoint is included; no arbitrary truncation or underflow cutoff is used.

The winning witness is recomputed with independent 80-digit direct products.
Bounds use a floating-point safety allowance but NOT directed interval rounding:
these are numerically checked enclosures, not machine-verifiable exact proofs.
Scores use the frozen baseline lower bound divided by candidate upper bound.
An unresolved enclosure (8 oracle CPU seconds or 50,000 subdivisions), overflow,
or high-precision discrepancy fails closed with an explicit reason. This resource
limitation can reject pathological valid node configurations; it is public.

## Freeze protocol

`--calibrate` runs only the provided baseline and emits measurements, not a fresh
attempt. After inspecting measurements, freeze `reference.json` and public target
before any fresh attempt. Never recalibrate during scoring. The suite and oracle
checksums prevent silent drift. `passed` means only that the fixed numeric target
was met; no difficulty/achievability classification follows from calibration.
