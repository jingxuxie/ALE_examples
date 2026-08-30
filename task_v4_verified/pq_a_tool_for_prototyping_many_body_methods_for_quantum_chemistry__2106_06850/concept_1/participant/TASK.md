# Memory-bounded many-body contraction planning

Develop a reusable planner for batches of tensor contractions arising in generated coupled-cluster, left-state/density, and response kernels. Reduce arithmetic while preserving every requested tensor and respecting a hard scratch-memory budget.

The input directory supplies representative batches and baseline measurements. The workspace contains the exact plan validator and interface specification. The runnable baseline independently optimizes each contraction; your planner may reuse intermediates across the batch.

Submit `solve.py` and any dependencies you implement in your output directory. Invocation is `python solve.py INPUT.json OUTPUT.json`; the output is a declarative contraction plan, not executable tensor code. Only the standard library, NumPy and SciPy are guaranteed.

Hidden evaluation uses the same contract on different generated batches and orbital dimensions. Each invocation has 30 wall seconds, one CPU thread and 2 GiB address space. Every plan must be valid and obey its supplied memory cap. Success requires a geometric-mean arithmetic speedup of at least **1.75** over the supplied baseline and at least **1.15** geometric-mean speedup in **each** kernel family. Planning time, peak scratch usage and worst-family performance are reported separately.

You have one hour to develop the planner. No network access or external source repository is supplied.
