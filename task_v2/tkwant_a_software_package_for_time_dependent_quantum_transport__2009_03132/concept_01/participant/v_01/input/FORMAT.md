# Physical and artifact contract

## Input

A suite is `{"cases": [case, ...]}`. Complex matrices are represented as `{"real": [[...]], "imag": [[...]]}`. All indices are zero-based orbital indices; Hermitian matrices contain both triangles. `hamiltonian` is the central-region H at t=0.

Each lead has `cell` = H₀, `hop` = V, and `contact` = C, with shapes m×m, m×m and N×m. For outward cells numbered 0,1,..., the matrix block H[n+1,n] = V, H[n,n+1] = V†, H[central,0] = C. Leads extend forever. The `mu` and nonnegative `temperature` give f(E)=1/(1+exp((E−mu)/temperature)), with f(E)=1 for E<mu and 0 for E≥mu at zero temperature. `bound_mu` and `bound_temperature` use the same convention for all normalizable initial eigenstates of the coupled infinite system. No pairing terms or Nambu redundancy occur in this task. Spin/orbital indices count independently.

`drives` is a list. Their changes to H add together. An entry `[destination, origin, real, imag]` lists only one triangle, and its Hermitian conjugate is implicit when destination≠origin. For `kind="add"`, its complex coefficient multiplies the signal s(t) and is added to H. For `kind="phase"`, the coefficient is the initial H[destination,origin] and its change is coefficient×(exp(−i s(t))−1). A `contact_phase` has a `lead` index instead of entries and applies this phase change to the entire C block of that lead. It does not change the reservoir Fermi function.

Each drive has `profile`, `amplitude` A, positive `duration` τ, and optional `start` (default zero). Put u=max(0,t−start) and q=min(1,u/τ):
- `ramp`: s=A(1−cos(πq))/2.
- `pulse`: s=A sin²(πq), returning to zero after τ.
- `voltage_phase`: s=A[u−τ sin(πu/τ)/π]/2 for u<τ and A(u−τ/2) afterward. This is a phase, not an instantaneous voltage.
- `ac`: s=A(1−cos(πq)) sin(omega×u)/2, with the supplied `omega`.

`times` is a strictly increasing list starting at 0. `current_bonds` lists pairs `[destination, origin]` inside the central region. The reported current is particle flow from origin to destination:

`J(destination <- origin) = 2 Im[H[destination,origin](t) × <c_destination† c_origin>(t)]`.

For an occupied one-particle state ψ, the correlator in that expression is ψ[destination]* ψ[origin]. This convention makes the sum of currents entering an orbital equal its density derivative. Density is `<c_index† c_index>`, not a difference from time zero. Do not sum spin or orbitals beyond what the requested bond explicitly says.

## Batch output

For each case ID, emit `ID.npz` with:
- `times`, shape (nt,);
- `density`, shape (nt,N), real;
- `current`, shape (nt,nbonds), real.

Emit `ID.json` with actual `config` dictionary, `seconds`, `peak_rss_mb`, and any useful diagnostics. A batch also emits `results.csv`. Paths are supplied at invocation and must not be hardcoded. Numeric summaries are:

`row_id,case,family,config,initial_charge,final_charge,peak_current,transported_charge,max_density_change,runtime_s,peak_rss_mb`

Row ID is `case_id:config_name`. Charges are sums of all central densities at first/last times. Peak current is max absolute value over times and requested bonds. Transported charge is trapezoidal integration of the first requested bond over the supplied times (a table-summary convention, not an independent high-accuracy physical integral). `max_density_change` is max abs(density(t)−density(0)). Runtime and RSS must be measured, not guessed. The supplied writer defines these summaries completely.

For the evidence package, traces and metadata reside in `runs/production/`, `runs/conservative/`, `runs/ablation/`, and `runs/scaling/`. The top-level `results.csv` contains all six production development rows; `ablation.csv` contains all development conservative and ablation rows; `scaling.csv` contains all production control rows. Configuration names must correspond to real executed code. You may add diagnostic columns and additional experiments without removing the required ones.

## Claims

`claims.json` is an object with a `claims` list. Include at least three substantive, bounded claims, linked to evidence. Every claim has `id`, `text`, `left`, `comparison`, and either `right` or `value`. A table cell is `{ "table": "results.csv", "row_id": "fp_development:production", "column": "peak_current" }`. Supported comparisons:
- `le`, `ge`: compare two referenced cells or a cell and a scalar `value`.
- `abs_difference_le`: two cells, plus nonnegative `tolerance`.
- `relative_difference_le`: two cells, nonnegative `tolerance`, using abs(left−right)/max(abs(left),abs(right),1e−12).

Explain the physical interpretation and limitations in `text` and `report.md`. At least one claim must compare a production row to an ablation/refinement row and at least one must concern measured time-horizon/resource behavior. A passing arithmetic comparison alone does not establish a universal physical claim.

## Figures

The primary plot must expose transient behavior. Its CSV contains `case,config,time,density_sum,current_0`, drawn from the raw traces. The robustness/scaling plot's CSV contains `row_id,runtime_s,peak_rss_mb`, drawn from the tables. Both PNGs should be generated from those sources. Layout, font, color, and pixel matching are not graded.
