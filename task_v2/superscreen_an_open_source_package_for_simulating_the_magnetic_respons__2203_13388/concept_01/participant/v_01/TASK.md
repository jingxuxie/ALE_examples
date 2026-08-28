# Qualify the thin-film device-response pipeline

You are taking responsibility for the numerical qualification of a superconducting
device simulation pipeline. The laboratory uses it to choose circulating currents,
prepare trapped-flux states, and predict what a nearby magnetic sensor will read.
The legacy pipeline runs, but its reassuring scalar diagnostics do not establish
that its current distributions, readout fields, and inductance matrices describe
the same physical device. The planned devices include patterned films and tightly
spaced screening layers, outside the benign regime used for the original adapter.

Deliver a repaired or replacement executable workflow and experimental evidence
showing which results can be trusted. Do not merely symmetrize reported matrices,
increase an iteration count, or suppress warnings. Investigate the disagreement
between state preparation, spatial response, and physical consistency. You may
modify any supplied implementation or replace components; no specific numerical
method is required.

## Starting point

- `workspace/superscreen/`: a real scientific package, including its native FEM,
  single-film solver, iterative film coupling, fluxoid and field-readout routines.
- `workspace/device_layouts/`: real device-layout construction code.
- `workspace/qualification/`: the laboratory's extraction/qualification adapter,
  configuration selection, experiment driver, summaries and figure generation.
- `input/`: four unlabeled development devices. Each has a JSON description and
  an NPZ mesh/source archive; `suite.json` lists the development experiments.
- `workspace/runtime/`: pinned offline Python dependencies. Installation and
  internet access are not needed or permitted.
- `workspace/PHYSICS.md` and `workspace/INTERFACE.md`: the physical and executable
  contracts. Read these before interpreting a numerical discrepancy.

The adapter's numerical approximations are not a specification. In particular,
the supplied material map, topology, prescribed sources, and sheet-current model
take precedence over an approximation chosen by the legacy adapter. Meshes are
provided so qualification is not dominated by mesher installation or CAD work.
The target is the resolved piecewise-affine thin-sheet model on those meshes, not
a fit to the legacy outputs. Arbitrary remeshing is not required.

## Work to carry out

1. Reproduce and diagnose the baseline. Use controlled changes to distinguish
   discretization, material representation, film coupling, state control, and
   readout errors. A small algebraic residual is not by itself a physical check.
2. Repair or replace the relevant components. Resolve the device's coupled
   response, including imposed circulating currents and imposed fluxoids, and
   produce reliable near- and far-field predictions.
3. Run the development suite with your chosen configuration and at least one
   meaningful alternative or ablation. Keep enough raw outputs to reproduce
   your tables and to identify which change caused an observed improvement.
4. Measure runtime and memory across the supplied device sizes. Separate
   compilation/setup costs when interpreting the measurements, and explain
   whether the method remains practical for repeated excitations of one device.
5. Write a concise technical report. State what failed, what you changed, what
   your experiments establish, and what they do not establish. Do not claim
   experimental validation of the London model from numerical agreement alone.

This requires a real run–inspect–revise–rerun loop. Record its evidence in the
report; do not manufacture pre-repair results. Public invariants are useful
diagnostics but not a complete correctness oracle.

## Deliverables in your assigned output directory

```
run.sh
workspace/                  executable repaired system
results.csv                 chosen-configuration development measurements
ablation.csv                measurements for distinct configurations
scaling.csv                 measured time/memory/size
raw/<configuration>/*.npz   numerical outputs backing the tables
figures/primary_result.png
figures/robustness_or_scaling.png
claims.json
report.md
```

The provided experiment driver and plotting code can be reused. Figures must
come from the submitted tables; appearance is not graded. You need not copy
`workspace/runtime/` into your output: `ALE_RUNTIME` will point to the supplied
runtime when your entry point is rerun. All other solution code must be in your
output directory. Do not depend on modifications left only in the input workspace.

## Running and diagnostics

From this task directory:

```
source workspace/environment.sh
bash workspace/run.sh suite input/suite.json /path/to/your/output/baseline
python -m qualification.diagnose input/suite.json /path/to/your/output/baseline
python -m pytest workspace/tests -q
```

Your final entry point must also accept:

```
bash OUTPUT/run.sh case CASE.npz OUTPUT_RESULT.npz [--config NAME]
bash OUTPUT/run.sh suite SUITE.json OUTPUT_DIRECTORY
```

The default configuration must be your qualified implementation. The evaluator
will pass previously unseen devices and sources; it will not import a particular
function or require a particular implementation. It supplies `ALE_RUNTIME` and
an otherwise offline Linux/Python 3.10 environment.

## Qualification conditions

Held-out devices span annular inductors, asymmetric multiply perforated films,
real multilayer pickup/field-coil layouts, close screening stacks, spatially
patterned effective penetration depths, and vortex-bearing slotted films. Some
are driven by current, some by an applied field with fluxoid constraints, and
some combine these conditions. Separations can be well below a mesh edge length;
zero-thickness sheets are still the intended model. Material coefficients can
change across element boundaries. These changes are not unknown parameters to
infer: their definitions are supplied with each evaluation input.

Behavior is evaluated against an independently checked high-accuracy realization
of the same resolved physical model: spatial streams and currents, vector
readout fields, hole currents/fluxoids, and the full inductance response. Scores
vary continuously with relative error; a typical 1% error is materially better
than 5%, and localized failures matter. Average and worst-family accuracy both
count. Runtime and memory compete with fidelity. A practical target is seconds
to tens of seconds per device on one CPU thread; an evaluation process has a
60-second safety cap and a 4 GiB resident-memory ceiling. These are generous
relative to the supplied device sizes (roughly 100–350 vertices, up to 600
triangles, four excitations), not a request to omit physical effects.

Tables, raw arrays, ablations, and claims will be checked against one another and
against reruns. Unsupported claims or missing clerical artifacts cannot turn an
otherwise correct core into evidence of a scientifically difficult failure.

Work only in this task directory and your assigned output directory. Do not
search for external solutions, use the network, or inspect other task versions,
reference solutions, evaluator files, or other agents' work.
