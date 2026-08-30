# Submission

The certificate data is in `output/answer.json`, with an identical copy at
`answer.json`. These JSON files are self-contained; no solver code is needed
to evaluate them.

`validation.json` records the public checker's assessment of the selected
certificates. The Python scripts and logs are retained as search diagnostics.
The search combines positive-matrix semidefinite relaxations, rank-one
nonlinear fitting, support refinement, and continuous dimension refinement.
