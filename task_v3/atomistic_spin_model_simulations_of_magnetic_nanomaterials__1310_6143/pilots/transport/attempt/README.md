# Resolved multisublattice transport

## Run

```sh
python solve.py CASE.json OUTPUT.json
```

`solve.py` is a self-contained Python 3.10+ implementation using only the standard
library. It needs no vendor packages, reference data, network access, build step,
or persistent state. The output is one JSON object with all eight required keys,
in the original cell, stack, and atom order. JSON serialization rejects nonfinite
numbers.

## Implementation

1. Group atoms by cell and sublattice. Compute moment-weighted reduced
   magnetizations without unit normalization, total channel moments, and
   atom-count means of resistivities and transport coefficients. Use the actual
   channel atom fraction for its conducting area. Summations use `math.fsum`.
2. Traverse each stack in the selected direction. Remember the last occupied
   reduced magnetization separately for each sublattice; an interior vacancy
   does not replace it. Entrance channels have only ordinary resistance and
   exactly zero transport field.
3. Combine occupied channels in parallel inside each cell, cells in series
   inside each stack, and stacks in parallel. Allocate branch currents by
   conductance at the shared local cell voltage. Missing channels carry zero
   current, rather than acting as short circuits.
4. Apply the specified field formula with the fixed factor `35486911.9121`,
   channel current, channel moment, and count-averaged coefficients. Map the
   resulting field to each original atom, then evaluate its transport-only
   Landau–Lifshitz–Gilbert derivative using that atom's spin and damping and
   `gamma = 1.760859e11`. There is no extra moment division in the derivative.

Both time and storage scale as O(atoms + cells × sublattices), apart from JSON
parsing and serialization, which are linear in input/output size.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_solve
PYTHONDONTWRITEBYTECODE=1 python benchmark.py
PYTHONDONTWRITEBYTECODE=1 python benchmark.py --direction 1 --output-dir validation_forward
```

The tests include analytical electrical/field/derivative results; unequal
moments and atomic damping; compensated, collinear, and zero-reduced order;
sparse-channel memory and reversal; atom reordering; rotational covariance;
voltage, moment, resistivity, and geometry scaling; zero voltage; conservation;
tangency; and the command-line interface. An independent 60-digit Decimal
implementation checks all output quantities on 32 randomized small stacks.
It finds upstream polarizations by explicit backward search and evaluates the
double cross product through the vector triple-product identity.

Set `TRANSPORT_EXAMPLES` to the supplied public `input` directory to additionally
check all three public examples against the Decimal implementation. All 15 tests
passed here with these examples enabled. They are optional validation inputs,
not runtime dependencies.

The benchmark generates 50,000 atoms, 512 cells, 16 stacks, 8 sublattices, and
64 materials, including missing interior channels. It times the complete solver
process with `/usr/bin/time` under a 1 GiB address-space limit, then verifies
shapes, finite outputs, zero entrance response, current conservation, and
tangent derivatives. Generated cases, outputs, and timings stay in its selected
output directory. The reverse-direction run here took **1.60 seconds** with
**46,652 KiB** peak resident memory. Its maximum relative cell-current
conservation error was `3.33e-16`; its maximum relative tangency residual was
`2.66e-15`. The forward-direction run took **1.24 seconds** with **45,704 KiB**
peak resident memory, `3.33e-16` maximum relative cell-current conservation error,
and `3.60e-15` maximum relative tangency residual. Timings depend on the execution
environment. Large generated benchmark inputs and outputs were removed after
validation; the timing records remain, and `benchmark.py` regenerates the cases.

## Scientific scope

This implements the version-1 local transport closure, not a microscopic or
self-consistent electronic transport calculation. It does not include spin
diffusion, lateral currents, exchange/anisotropy fields, thermal noise, or time
integration. Reduced order is resolved only to the provided cell-sublattice
averages; all atoms in a channel share its field. These are limitations of the
specified model rather than additional cell-averaging approximations in this
solver. Numerical validation is against analytical checks and the independently
implemented contract, not an external physical reference.
