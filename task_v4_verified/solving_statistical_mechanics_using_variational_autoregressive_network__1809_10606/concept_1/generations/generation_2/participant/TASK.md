# Compact equilibrium models for frustrated materials

Improve the supplied champion's normalized equilibrium proposals for disordered
Ising materials with interacting regions. The replacement must preserve both
variational accuracy and probability mass needed for reliable reweighting.

`input/` contains public examples; `baseline/solve.py` is the current champion.
The Hamiltonian, eight-component autoregressive-mixture artifact, and exact
quality metrics are specified in `workspace/INTERFACE.md`; numerical utilities
are in `workspace/van.py`.

Submit `solve.py` and its dependencies. On each unseen 20-spin instance, the
evaluator runs `python solve.py INSTANCE.json MODEL.json`. Each invocation gets
120 seconds, four CPU cores, 8 GiB address space per process, and no GPU/network.
All instance-specific fitting is charged. Use Python, NumPy, SciPy, PyTorch,
and the standard library. Development time is one hour.

Pass all exact-enumeration goals: mean reverse KL at most **0.04 nats**,
worst-family mean at most **0.06 nats**, overall KL at most **40%** of the
champion's, every family's KL at most **50%** of the champion's corresponding
mean, and population ESS fraction at least **0.25 on every instance**.
Three material families differ in region sizes and disorder. Invalid artifacts
or exceeded limits fail; the artifact capacity is unchanged at eight components.
