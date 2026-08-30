# Reliable compact equilibrium proposals

Replace the supplied annealed variational baseline with a solver that compresses
finite, frustrated Ising equilibrium distributions into small normalized
autoregressive mixtures. Good variational free energy alone is insufficient: the
proposal must also retain the probability mass needed for reliable reweighting.

The public inputs, numerical model utilities, and runnable baseline are in
`input/`, `workspace/`, and `baseline/`. `workspace/INTERFACE.md` defines the
Hamiltonian, artifact format, and quality metrics.

Submit `solve.py` and any dependencies in your output directory. The evaluator
runs `python solve.py INSTANCE.json MODEL.json` on unseen instances with 18–20
spins, drawn from dense disordered, associative-memory, and frustrated-lattice
families. Return a mixture of at most eight triangular logistic models.

Each invocation has 120 seconds of wall time, four CPU cores, 8 GiB memory, and
no GPU or network. All fitting for an unseen instance counts toward that budget.
Only Python, NumPy, SciPy, PyTorch, and the standard library are available.

Pass requires exact mean reverse KL at most 0.12 nats, worst-family mean at most
0.20 nats, at least 60% improvement over the supplied baseline's mean reverse KL,
and population importance-sampling ESS fraction at least 0.25 on every instance.
Invalid artifacts or exceeded limits fail. You have one hour to develop the solver.
