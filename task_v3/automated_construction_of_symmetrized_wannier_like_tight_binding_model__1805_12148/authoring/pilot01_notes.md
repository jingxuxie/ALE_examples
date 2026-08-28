# Pilot 01 — covariant import and cell pipeline

## Pre-build anti-compression check

Read candidate_gaps.md A and F before implementation. Selected a bounded A+F
mission: repair import semantics and same-volume cell/origin transport, **not**
a group-average puzzle. The group-projection alternative is deliberately out
of scope. Three separately scored families are Cartesian/Wigner–Seitz import,
nearest-atom import, and gauge-resolved cell mapping. The geometric track gets
its own correct input hopping model, so an import failure cannot erase its
credit. Neither sorted bands nor one Fourier/group-averaging kernel solves all
three: units and file degeneracies, Cartesian atom correspondence, and integer
lattice/orbital gauge transport are independent bottlenecks.

Pre-build shortcut audit: ignoring wsvec changes off-grid Hamiltonians; using
fractional Euclidean distance can change atom correspondence in skew cells;
matching bands alone misses orbital phases; truncating floating lattice vectors
loses hoppings even when their rounded values are integers. Public data will
contain one small invariant-only smoke case, no target tensors. Private cases
retain all orbitals/hoppings from official fixtures; no band/subspace truncation
or toy-model substitution is allowed. Primitive Si/Bi import files have 8/10
orbitals; their requested physical two-cell supercells have 16/20 orbitals.
Native nonsymmorphic Si has 16 orbitals, and official 14-orbital InAs is used
as a full 28-orbital physical supercell. This enlargement is not a duplicated
block-diagonal toy: intercell hoppings remain connected.

## Source pins and genuine defects

Repository: authoring/sources/TBmodels, immutable read-only input.
Privileged reference pin: 39d7eb096d809137373774ef6ba337fdf36349bc,
src/tbmodels/_tb_model.py. Use source before authoring/vendor on PYTHONPATH.

- a93b8f805b3ade4436a89dffb209ae1d2f857dbd: tbmodels/_tb_model.py,
  from_wannier_files, before bc20bcba655eb282592a8315ee40eae30eed638e.
  XYZ Cartesian positions are consumed as reduced positions.
- 0168836c6bb2c04ac7a9d4ac6682fca47512ea4c: tbmodels/_tb_model.py,
  from_wannier_files, before 84cdd38d47243208b49c88e8e41c449201530df7.
  The actual bug is a missing norm axis (one scalar distance selects atom 0),
  not merely a fractional-metric typo. Cases also challenge fractional metrics.
- 24c3d2b3420d7b4b34ae15c636ea2f3685fbf02d: tbmodels/_tb_model.py,
  change_unit_cell and its dense dependencies, before merge
  eb5393c77ce2b4a15ce603789a084947fdee58d6. Integer validation rounds but the
  old remapping uses an unrounded floating new_R before integer conversion.
- 1c2c1020e1fb344cc4cc4d65f2350d2efe009710 was audited but is not used:
  no claim to evaluate nonsymmorphic or antiunitary projection in this pilot.

Official fixtures at the reference pin: tests/samples/silicon_{hr,wsvec}.dat,
silicon_centres.xyz, silicon.win; corresponding bi files;
examples/symmetrization/nonsymmorphic_Si/data/model_nosym.hdf5;
tests/samples/InAs_nosym.hdf5. Exact selected-method/source hashes and case
transform metadata will be stored privately by the builder.

## Scope and isolation

Only pilots/01_covariant_pipeline/** and this note are writable. Shared sources
and vendor must not be edited. Participant package contains historical extracts,
NumPy-only dense compatibility scaffolding, the task/schema, and one unlabeled
smoke input. Later code, build scripts, labels, scores, and seeds stay private.
The parent runner must mount only participant/ and a writable attempt/, not
private/ or authoring/. Subprocess scoring alone is not a filesystem sandbox.
No subagents launched. Dependencies import successfully as of this audit.

## Build and validation record

The first independent text check caught a semantic mismatch: current TBmodels
nearest-atom import searches periodic images, unlike the 2017 explicit-atom API.
The reference now uses the exact fixed method at
84cdd38d47243208b49c88e8e41c449201530df7 (private/atom_reference.py), inherited
over the current model infrastructure. This preserves the explicitly specified
input semantics and uses an official later fix, not a custom solution.

### Built artifacts and data fidelity

- Public: concise TASK, separate SCHEMA, exact historical method extracts,
  dense-only constructor compatibility, runnable baseline, and one invariant-
  only smoke case. No modern repair code, labels, split manifests or seeds.
- Private: 18 complete cases, six each for test/challenge/confirmation, frozen
  reference and weak NPZs, exact provenance/transformation manifests, a fresh-
  computing official-source strong entrypoint, a label-only evaluator, and an
  acceptance validator. The evaluator never imports the reference engine.
- Output dimensions: 16 (Si), 20 (Bi), 28 (InAs). The mapping track uses native
  16-orbital Si or a genuinely connected 28-orbital InAs supercell. No orbitals
  are removed. The official Bi test fixture itself is 10-orbital and diagonal
  in primitive orbital indices; it is not claimed to be a new full Bi ab-initio
  calculation. It remains useful for format/position checks, and each Bi case
  also carries the independent coupled 28-orbital InAs mapping input. Actual
  nontrivial wsvec interpolation is tested on the complete official Si fixture.
- Import transformations: source text preserved structurally, Cartesian
  affine embedding and common origin shifts, atom row permutations, constant
  diagonal orbital-unitary phases, positive energy rescaling, true two-cell
  supercells, output permutations and off-grid k points. InAs is exported by
  the official HR serializer. These are controlled transformations of source
  models, not claims of recalculated strained-material electronic structure.
- Mapping transformations: full native Si or full InAs physical supercell,
  input orbital permutation, Cartesian embedding, diagonal orbital gauge,
  determinant-one shears, near-boundary origins, Cartesian/reduced API modes,
  target ordering, and fresh off-grid k points. Serialized list inputs are
  checked during construction to avoid an unrelated exact-determinant issue.
- Reserved confirmation seeds 930071–930076 use inverse shears, different
  embedding stretches and supercell axes. Test seeds are 120031–120036;
  challenge seeds are 470041–470046. No participant attempts or agents have
  consumed these cases. Confirmation was not changed after the shortcut audit.

### Empirical anti-compression follow-up

The actual old failure is demonstrated on every case, not injected: old XYZ
units/atom correspondence lose import accuracy, and pre-eb5393c floating-cell
vectors lose hopping support during remapping. The weak errors and complete
weak outputs are frozen per case. Import-only repair leaves cell_gauge at 0.1;
mapping-only repair leaves both import families at 0.1. Bands-only repair does
not recover the matrix-valued score. Ignoring the Si wsvec corrections yields
nonzero interpolation error; Bi's diagonal fixture does not provide that stress.

The first fractional-distance ablation did not distinguish the mild embeddings.
Before any participant launch, the Si nearest-atom test/challenge cases were
strengthened by selecting source-preserving anisotropic embeddings for which
Cartesian and fractional assignments differ. Their full 8-orbital source is
still expanded physically to 16, and their paired mapping input remains the
full native 16-orbital Si model. This is recorded explicitly rather than claiming
the initial mild skew already defeated that shortcut. There is no claim that
a capable participant cannot quickly locate the three local historical defects;
the parent runner determines actual solve difficulty.

### Validation and launch

Final validation passed after re-evaluating both strengthened cases. Reference
core and worst-family scores are 1.0 on test, challenge and confirmation; the
historical baseline is 0.1 on every family and split. All 18 cases pass the
independent checks, with maximum absolute residual 2.808864252301646e-14.
The fractional-metric shortcut makes four wrong primitive assignments across
the strengthened cases. Import-only repair scores 0.4641588834 overall,
mapping-only repair 0.2154434690, and bands-only repair 0.1023352737. All ten
distinct source fixture hashes match their exact committed Git objects;
private/validation/source_audit.json records that check. Final authoritative
numbers and residuals are in private/validation/reference_validation_report.json
and the strong_*.json / weak_*.json evaluator reports. Independent checks include
direct text-to-supercell complex matrices, Cartesian position assignment,
Bloch convention conversion, Hermiticity, primitive/supercell spectral folding,
geometric covariance and inverse-cell H1 transport. Subprocess-environment,
partial-output, shape/finiteness, pickle and timeout checks are also included.

From pilots/01_covariant_pipeline:

```
python attempt/solve.py --input participant/input/smoke --output attempt/smoke.npz
python private/evaluator.py --submission attempt --split test --output private/validation/report.json
python private/evaluator.py --submission private/strong --split confirmation --output private/validation/strong_confirmation.json
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python private/validate.py
```

Use --split challenge or --split confirmation for their frozen pools. The
evaluator stages only case inputs and constructs a clean subprocess environment
without authoring PYTHONPATH/PYTHONHOME. Actual filesystem/network isolation is
the parent's central runner responsibility. Namespace setup failures must be
treated as infrastructure failures and retried with the necessary outer
approval, not scored as solver failures. No shared source/vendor edits and no
subagents were used.

## Pre-launch isolation integration

Submitted-code execution now calls the parent's authoring/sandbox_exec.py
run_submission helper with the actual case directory, public participant tree,
90-second timeout, and 4 GiB memory limit. Helper return fields are translated
to the existing per-case runtime/error schema; core_score, worst_family_score,
family_scores and per_case remain unchanged. Namespace RuntimeErrors propagate
as infrastructure failures, never zero solver scores. The exact private/strong
reference branch keeps its original execution path and dependencies. Numerical
references and existing validation reports were not regenerated or modified.

Helper loading does not change PYTHONPATH or create shared-authoring bytecode.
Submitted scratch outputs and sandbox probe fixtures live within the pilot,
outside /tmp, because bwrap replaces /tmp. The initial attempt/solve.py has been
removed; attempt/ is empty for the parent launch. The historical baseline remains
in participant/workspace and can be evaluated without populating attempt/.
No runner or nested-namespace evaluation was launched during this integration.

Parent-approved evaluator command (outside the outer sandbox, keeping bwrap):

```
python private/evaluator.py --submission participant/workspace --split test --output private/validation/isolated_weak_test.json
```

After the parent populates attempt/, use --submission attempt for participants.
