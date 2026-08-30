# Final ratchet 3: ready for parent review

Inactive package only. No new fresh agent was launched. The active generation-2 participant, evaluator and status are unchanged.

## Fixed target

Unchanged mode A: core >= 0.90 (18/20), worst family >= 0.75 (3/4 each), and worst-family improvement >= 0.25 over the original public baseline. Gap residual <= 2e-8, Z residual <= 2e-9, branch distance <= 0.002 with the same nonzero/sign guard. Each case gets 12 child CPU seconds, 2048 MiB, one process/thread and an 1800-second wall safety ceiling.

## Scores and selection

The unchanged public weak baseline scores core 0.40 / worst 0.00. Actual fresh v4 scores core 0.80 / worst 0.50, failing exactly the four selected cases at the CPU limit. The final replay uses its frozen submission directory only; no privileged archival report is mounted with the candidate.

Replace case_06/07/16/17 with continuum_04/06/02/03. All other sixteen cases are byte-identical, including all four nearcritical branch-hard cases and the two representative 32768-frequency critical cases. Maximum patch and Matsubara dimensions stay 40 and 32768.

## Physical and numerical evidence

The four new instances use 96 distinct positive log-frequency quadrature nodes, smooth five-peak patch-pair spectra, fixed moderate integrated coupling, varying noncommuting anisotropy, and the original physical frequency window. They are synthetic finite-cutoff Eliashberg inputs, not ab initio material predictions. The sampled normalized kernels agree with 192-node quadrature within 4.78e-11 over 80 transfer-frequency probes; this is a quadrature audit, not an infinite-cutoff or continuum error theorem. No modes or patches are duplicated padding.

| Hidden slot | Probe | P x N | Pairing eigenvalue | v4 algorithm with deadline lifted |
| --- | --- | --- | --- | --- |
| case_06 | continuum_04 | 32 x 16384 | 1.354519 | 79.780 CPU s, quality passed |
| case_07 | continuum_06 | 24 x 32768 | 1.633733 | 44.592 CPU s, quality passed |
| case_16 | continuum_02 | 32 x 32768 | 1.750331 | 90-CPU-s limit reached; no output |
| case_17 | continuum_03 | 40 x 32768 | 1.995668 | 90-CPU-s limit reached; no output |

Builder-owned full-grid Newton references converge from two independent amplitude starts. Independent uncombined signed convolutions and direct signed rows certify residuals <= 1.7e-14; cross-start branch distance <= 7.2e-16. The public 96-node / 4096-frequency example is a separate draw with its own private nonzero-branch certificate.

The extended control imports the byte-identical actual v4 code only inside the sandbox and lifts only its internal deadline. It does not demonstrate 12-second attainability. The joint large/nearcritical pool was not selected: actual v4 passed all four in at most 2.475 CPU seconds. This ratchet therefore targets a genuine resolved-spectrum computational cost gap, not a smaller critical margin or a polynomial-degree trap.

## Audits and privacy

29/29 numerical/security tests and 180/180 continuum checks pass. Evaluator, field checker, sandbox runner, public operator, baseline and workspace source hashes are unchanged. The first test invocation used the host's symlinked /home TMPDIR and correctly triggered the source-path protection; rerunning with canonical /srv TMPDIR fixes only launcher plumbing, with no weakened security check.

Previous fresh code remains private in champions/generation_3 and adversary. The participant package adds only scope documentation and one public input NPZ. No private eigenmodes, branch arrays, sheet labels or generator seeds are exposed.

## Artifacts and runtime

- Pending task: package/concept_1; sibling package/authoring/sandbox_runner.py.
- Seal: package/concept_1/evaluator/hidden/prelaunch_seal.json, with files mapping for the parent activator.
- Full scores: package/concept_1/attempts/baseline_report.json and previous_fresh_report.json.
- Evidence: ratchet_evidence.json; original pool, continuum generation, certificates and timing controls remain runnable in ../prospective_generation3.
- Generation-2 archive: generation_2_runnable_snapshot.tar.gz plus generation_2_snapshot_manifest.json; exact shared runner included at its expected sibling path, archived evaluator smoke passed.

Conservative additional authoring accounting is 1357.5 CPU seconds against the 1800-second continuum budget, separate from the original 520.8-CPU-second joint pool. Recommend the parent's 3600-second fresh trial, retaining the fixed 12-CPU-second / 2-GiB / one-thread candidate gate and generous wall ceiling. Joint generation-3 speed/quality attainability remains unknown; difficulty is provisional until the final allowed fresh trial.
