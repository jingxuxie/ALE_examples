# Find a compact silent GQSP compilation failure

You are auditing the numerical reliability of compact quantum signal-processing blocks. Produce a dense, strictly contractive complex polynomial of degree **8 through 14** for which the supplied Qualtran FFT-completion and phase-extraction pipeline returns an inaccurate quantum transformation, even though completion succeeds accurately and no near-zero phase branch is taken.

The frozen numerical method, a local diagnostic, source provenance, and a runnable starting candidate are provided. The complete artifact format, admissibility requirements, six evaluation configurations, and score are in `workspace/interface.md`.

Submit `counterexample.json` in your output directory. This is a data-only submission; evaluation does not execute your code. All six configurations must have phase-invariant RMS amplitude error at least **0.05**. Invalid inputs, inaccurate complements, crashes, and near-zero phase branches do not count as counterexamples.

Use the available one-hour session. The evaluator allows 60 seconds and at most 64 KiB of submitted JSON. No full quantum simulator or reference solution is required.
