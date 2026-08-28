# Coded-index counterexample probe: also solved

This is an additional audit of the existing sparse concept, not a fifth pilot,
a ratcheted participant task, or another model attempt. The first sparse audit
already found all twelve standard-domain boundary cases solved. We additionally
checked whether the follow-up's full coded-index branch supplies a missing gap.

## Privileged artifact and limits

The primary source is *Fast Estimation of Sparse Quantum Noise*, arXiv:2007.07901,
Section VII, equations (20)–(21), Algorithm 4. It separates noisy index decoding
from bin verification and peeling and allows a classical linear-code decoder.
BCH is our concrete instantiation, not a claim that the paper prescribed BCH.
The existing `jkent/python-bchlib` implementation is pinned at
`8d0656ab8f37e734428635501738d360ad80eebd` (source version 2.1.3), compiled only in
the private source directory. Its original license remains in that checkout.

`probe.py` composes that existing decoder with the original input-only peeling
and nonnegative refinement helpers. The trusted reference receives no labels.
The quantum observation generator is independently checked against physical
Pauli-character sums; maximum discrepancies are recorded per case. A separate
test checks systematic-code linearity, padding and bounded-distance correction.

All three cases have 100 physical qubits, 192 arbitrary-weight significant
errors, four commuting-hash groups and 128 bins. The same seven-key input and
three-key output schemas are retained. The 249-row case is within the original
stated typical offset count. The 372- and 453-row cases are explicitly
exploratory O(n)-row extensions, not secretly added original-contract cases.
The bin SNR is deliberately lower than the initial pilot. No case is excluded,
reseeded, or selected after looking at its score.

This bounded implementation verifies codeword residuals and hash consistency;
it does not claim the full paper's independent random/coding-offset proof or
all of its variance-propagation guarantees. Such a claim is unnecessary for
this empirical counterexample check. A promoted task would have needed to
disclose the code parameters and bit layout rather than require guessing them.
No task is promoted.

## Results

| BCH degree / correction strength | Offset rows | Minimum bin SNR | Reference | Frozen model | Both support F1 |
|---|---:|---:|---:|---:|---:|
| 8 / 6 | 249 | 2.1 | 0.994122 | 0.994096 | 1.0 |
| 9 / 20 | 372 | 1.7 | 0.994606 | 0.994584 | 1.0 |
| 9 / 30 | 453 | 1.6 | 0.993773 | 0.993830 | 1.0 |

The reference passes score >0.9, F1 >=0.98 and uncapped loss <0.1 on all three.
The frozen solver recovers all 576 significant labels; its maximum raw loss
is below 0.0091. Runtime is at most 3.53 seconds, versus 0.73 seconds for the
reference process, under the same 120-second / 2-GiB limits. Student executions
use the unchanged staged Landlock grader. The trusted reference additionally
uses the private BCH module and resource-limited subprocesses; it is not
presented as a single-file participant submission.

Inspection explains the result: the frozen solution already implements a
reliability-ordered linear-code decoder using the supplied offset matrix. Its
capability is more general than hard systematic-bit thresholding, so replacing
random check rows with BCH parity rows does not defeat it. This is neither an
answer-table exploit nor evidence of a new hard region. No ratchet follows.

Reproduce from this directory with `/usr/bin/python probe.py`; run
`/usr/bin/python -m unittest -v test_coding` for the independent coding checks.
`results.json`, the case inputs/truth/predictions, decoder diagnostics and
`run.log` retain the complete numerical evidence.
