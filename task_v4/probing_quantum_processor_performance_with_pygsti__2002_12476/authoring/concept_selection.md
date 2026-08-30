# Private concept selection

Generation date: 2026-08-28. This directory is never allowlisted for participants.

The seed paper is Nielsen et al., *Probing quantum processor performance with
pyGSTi*, arXiv:2002.12476. We inspected its GST, reduced-model, model-testing,
drift, RPE, and customization sections, the ancillary-script location, the
official repository, its release history and open issues, and official
Fisher-information and germ/fiducial design documentation. The old local task
package is inspected separately; its private artifacts are not participant assets.

## Candidate inventory

1. **Retained, A:** sparse, integer-shot, cost-constrained characterization
   design robust to coherent operating-point uncertainty, decoherence, and
   nuisance readout parameters. A nominal determinant-greedy baseline leaves
   a genuine robust optimization gap; no optimal reference is required.
2. **Retained, B:** a physical counterexample to a compressed characterization
   or validation protocol: the calibration conditions hold but an independently
   reproduced operational prediction fails. A deterministic witness checker
   can establish failure without trusting the submitted search program.
3. **Retained, D:** finite-shot prediction for latent-memory quantum processors,
   including structured long-circuit extrapolation. Hidden exact probabilities
   remove test-shot noise, while public observations retain realistic ambiguity.
4. **Not built, E:** active multiparameter phase calibration with aliasing,
   unknown contrast, and a pulse-time budget. Promising, but query isolation
   and statistical power need more infrastructure than static artifacts.
5. **Not built, F:** leakage-aware parameterization-preserving gauge optimization
   repair. Recent upstream fixes create an undesirable source-copy shortcut.
6. **Not built, A:** periodic circuit derivative simulation under a memory cap.
   Too likely to reduce to cached products and one standard algorithm.
7. **Not built, D:** confidence coverage for drift-contaminated randomized
   benchmarking. Good scientific target, but coverage estimation needs many
   independent repetitions and could conflate finite-test noise with hardness.
8. **Not built, C:** amplificationally complete minimal germ construction.
   Pure rank completeness is too easy to satisfy by invoking standard selection;
   its genuinely hard robust resource tradeoff is included in concept 1.
9. **Not built, B:** coherent-error cancellation in mirror circuits. Simple
   sign-cancellation examples make an unqualified version too easy.
10. **Not built, C:** leakage-safe recalibration pulse sequences. Less directly
    grounded in the paper's digital characterization interfaces.

## Primary-source provenance

- https://arxiv.org/abs/2002.12476
- https://arxiv.org/pdf/2002.12476
- https://arxiv.org/src/2002.12476v1/anc/runnable_code_listings.py
- https://github.com/sandialabs/pyGSTi
- https://github.com/sandialabs/pyGSTi/releases
- https://github.com/sandialabs/pyGSTi/issues
- https://github.com/sandialabs/pyGSTi/pull/666
- https://github.com/sandialabs/pyGSTi/pull/852
- https://raw.githubusercontent.com/sandialabs/pyGSTi/master/pygsti/algorithms/germselection.py
- https://raw.githubusercontent.com/sandialabs/pyGSTi/master/pygsti/algorithms/fiducialpairreduction.py
- https://pygsti.readthedocs.io/en/docs-preview/markdown/guides/gst/CheckYourDesign.html
- https://pygsti.readthedocs.io/en/docs-preview/markdown/guides/gst/FiducialsAndGerms.html
- https://pygsti.readthedocs.io/en/docs-preview/markdown/guides/gst/FewerCircuits.html

The retained tasks are new research problems, not requests to reproduce a
pyGSTi implementation. Public physics/specifications are separated from private
scenario draws, labels, optimizers, and tournament records.
