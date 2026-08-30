# Active spectroscopy of an interacting spin register

Identify a six-site quantum register from a limited number of finite-shot
experiments. Its exchanges, local fields, anisotropy, frustration, and detector
errors are unknown. You may choose preparations, evolution times, and coherent
midpoint interventions. The same controller must work across mixed-sign field-disorder regimes. Configuration changes are expensive;
the total shot budget remains 36,864.

Assets: `input/protocol.md`, `input/config.json`, labeled development examples,
the exact local simulator in `workspace/physics.py`, and the current-champion
controller in `baseline/solve.py`. Local simulations do not consume experiment
queries; only interaction with the evaluator's device does.

Submit `solve.py` and any dependencies in your output directory. It runs as
`python3 solve.py`, exchanging newline-delimited JSON over standard input/output
according to the protocol. It must not need network access or other files.

Each device allows 3 experiments of 12,288 shots, 120 CPU seconds, 180 wall
seconds, 2 GiB RAM, and four numerical threads. Generation allows one hour.
Score is one minus mean parameter RMSE after scaling each parameter by its
stated range. Passing requires overall score at least 0.970 and the lowest
regime score at least 0.950. Invalid protocols, missing answers, or exceeded
resources fail. All parameter ranges and device physics are public; device
parameters and measurement randomness are held out.
