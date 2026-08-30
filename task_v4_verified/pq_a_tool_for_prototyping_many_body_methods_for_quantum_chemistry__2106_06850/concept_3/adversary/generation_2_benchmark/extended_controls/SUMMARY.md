# Extended original-control evidence

| Original control | Fidelity | Gates | Wall seconds | Result |
|---|---:|---:|---:|---|
| sector_10_4 | 0.9900431962605092 | 18 | 596.926 | FAIL |
| sector_10_6 | 1 | 20 | 29.376 | PASS |

Each control had a 600-second outer bound, with 580 seconds assigned to the worker and startup/teardown margin. Both runs were healthy and stayed within the outer bound. N10_6 solved with the original width-2000/branches-60 beam. N10_4 ran that beam, fresh-prefix bridges, continuous refinement/pruning, the archived width-10000 beam2, and another fresh-prefix bridge phase; it did not pass.

**Portability is only partially reproduced under this bounded profile.** The archived complete session did solve N10_4; this audit does not reproduce that success within its selected 600-second portfolio. This is neither a claim of algorithm impossibility nor a full-hour failure. The extended profile differs from the earlier narrow beam3 candidate-selection probes, and selected new cases were not rerun under this stronger profile.

Both freshly generated public .dat inputs are byte-identical to the archived original public inputs. Only unchanged archived algorithms/binaries and path/index loading adapters were used; all solver checkpoints were generated fresh. No archived answer, checkpoint, certificate, or seed entered either certificate-free sandbox. The completed secondary implementation was inspected but not run.

Generation-two participant and evaluator-core hashes match before and after. No frozen-packet file was edited. See report.json, protocol_checks.json, provenance.json, and runs/<control>/trusted_score.json for exact commands, phase allocations, timeouts, and independent scores.
