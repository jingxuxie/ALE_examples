# Concept 2: compact inverse compilation as a circuit witness

Mode **C (WITNESS)**. The public mathematical object is a complete four- or
five-qubit unitary, not a hidden seed or a requested historical decomposition.
Any nearest-neighbor U3+CNOT circuit meeting the public budgets and numerical
equivalence thresholds is accepted. Search combines discrete entangling-edge
sequences with continuous rotations. Unconstrained dense-unitary decomposition
does not by itself establish a solution under these small CNOT budgets; a
fixed variational topology need not contain the target. These are reasons to
investigate hardness, not a demonstrated lower bound or a fresh-agent result.

## Source provenance

Sources were read on August 28, 2026.

- Suzuki et al., *Qulacs: a fast and versatile quantum circuit simulator for
  research purpose*, arXiv:2011.13524, version 4 (October 5, 2021), sections 3.1,
  4.3, and 4.6. Section 3.1 explicitly says “Qulacs does not support gate
  decomposition.” The paper supplies the dense-operation and variational
  simulation seed, not this challenge or its targets.
  Source: `https://arxiv.org/pdf/2011.13524`.
- Official Qulacs advanced guide, “IBMQ basis gate,” “2 qubit gate,” general
  matrix gates, and parametric circuits. It documents U3's single-qubit
  expressivity and the control/target convention. This task states its own
  matrix formula explicitly and does not depend on a Qulacs installation.
  Source: `https://docs.qulacs.org/en/latest/guide/2.0_python_advanced.html`.
- Official repository: `https://github.com/qulacs/qulacs`.
  Follow-up PR `https://github.com/qulacs/qulacs/pull/707`, merged March 17,
  2026, fixes a FusedSWAP insertion-position bug and adds a regression test.
  This motivates checking complete operator semantics independently; the task
  does not reproduce that bug or ask participants to repair it.

## Private construction and release boundary

`authoring/` and `evaluator/hidden/` are private. A private entropy-derived seed
creates mixed, nonperiodic nearest-neighbor topologies and generic rotations
from irrational expressions rounded to float64. Full dense Kronecker products
produce the public operators, with independent row-update reconstruction
checking every private witness. A private global phase also exercises
phase-invariant equivalence. Witnesses obey exactly the public budgets.
Only two-qubit CNOT is used as the public formatting demo; it reveals no
generating topology or rotations for the scored operators.

Release **only `participant/`** to a generation agent. Never release this file,
authoring source, evaluator source/hidden assets, private reports, or the outer
task directory. The runnable evaluator mounts only the submitted directory,
the selected public input, standard libraries, and an output directory into
its child process. It fails closed rather than executing code unisolated.
The grading kernel never uses a generating circuit to evaluate a submission.

The identity baseline is intentionally weak and is an executable control, not
evidence that a strong synthesis method will fail. The private perfect witness
demonstrates attainability only. No fresh generation agents are launched and
no tested fresh-agent submission is created. Freeze the supplied target hash
before any later one-hour generation attempt; do not regenerate after seeing
a participant's result.
