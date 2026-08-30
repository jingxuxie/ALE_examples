# Generation-only research

These files are never included in the participant allowlist.

* Dennis, Hope, and Johnsson, *XMDS2: Fast, scalable simulation of coupled stochastic partial differential equations*, arXiv:1204.4255, especially Sections 2, 3.2--3.6. Paper PDF archived in `sources/paper.pdf`.
* Original developer repository `https://github.com/GrahamDennis/xpdeint`, source archive captured 2026-08-28 in `sources/xpdeint.tar.gz`. The transform multiplexer explicitly performs graph search over transform representations with computation and communication costs. See `xpdeint/Features/Transforms/_TransformMultiplexer.py`, `xpdeint/Utilities.py`, `_FourierTransformFFTW3MPI.py`, and `_MMT.py` in the archive.
* Official documentation `https://xmds.sourceforge.net/` and its `reference_elements.html`, `worked_examples.html`, `optimisation.html`, and `faq.html` pages. Later release notes describe separated IP operators, reuse of unchanged-timestep IP calculations, adaptive multipath scheduling, and expanded Hermite-Gauss bases.
* Developer discussion `https://sourceforge.net/p/xmds/mailman/xmds-devel/` inspected for later maintenance and release context; January 9, 2026 discussion concerns HDF5 build integration, not a numerical reference answer.
* The GitHub issues/history pages and Debian source listing were inspected for later context. No prior successful submission for this paper was found in the local task tree during initial inspection. Existing tournaments for other papers were inspected only to learn the local allowlisted runner and evaluation-isolation conventions; they were not participant assets or numerical solutions.

Concept 1 deliberately extends the paper's transform-routing problem to shared intermediate representations, version lifetimes, and a hard memory bound. Its synthetic integer cost model is explicitly an optimization environment, not a measured XMDS runtime claim. Concepts 2 and 3 use the paper's interaction-picture/spectral simulation capabilities as scientific seeds; neither asserts that an XMDS implementation has the challenge's audited defect.

The three task builders are privileged generation agents. Tested agents are separate ephemeral `ultima-alpha` sessions started solely through the user-specified `run_allowlisted_codex.sh`, with only participant files and an initially empty output directory mounted. Authoring sources, hidden cases, private searches, other submissions, and evaluator code are excluded.
