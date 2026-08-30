# Reliable compact proposals across frustrated materials

Improve the supplied normalized equilibrium-model engine across weakly coupled
local sectors, interacting regions, and frustrated cycles. It must retain both
variational accuracy and the probability mass needed for reliable reweighting.

`baseline/` contains the current engine and `input/` contains public examples.
The Hamiltonian, eight-component autoregressive-mixture artifact and exact
metrics are specified in `workspace/INTERFACE.md`; numerical utilities are in
`workspace/van.py`.

Submit `solve.py` and its dependencies. On each unseen 20-spin instance, the
evaluator runs `python solve.py INSTANCE.json MODEL.json`. Each invocation gets
**120 seconds, four CPU cores, 8 GiB address space per process, no GPU/network**.
All instance-specific fitting is charged. Development time is one hour.
Use Python, NumPy, SciPy, PyTorch, and the standard library.

Pass every frozen objective: mean reverse KL **at most 0.04 nats**, worst-family
mean KL **at most 0.06 nats**, overall mean KL **at most 40% of the supplied
champion's frozen calibration**, and population ESS fraction **at least 0.25 on
every instance**. The three physical families are weighted equally. Invalid
artifacts and exceeded invocation limits fail. Model capacity stays at eight
components; no runtime callbacks or probability tables are accepted.
