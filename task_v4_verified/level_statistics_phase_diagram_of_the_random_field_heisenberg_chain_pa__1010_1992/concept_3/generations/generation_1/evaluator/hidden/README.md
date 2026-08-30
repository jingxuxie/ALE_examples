# Trusted evaluator inputs

`exact.py` is a byte-identical frozen copy of the public physics helper.
`protocol.json` is a byte-identical frozen copy of the public protocol.
Neither is loaded from a witness-supplied path or participant workspace.
There are no secret grading targets or secret perturbations. This directory
is evaluator-owned and must not be mounted writable in a participant run.
The evaluator consumes static JSON only and recomputes every eigenvalue.
