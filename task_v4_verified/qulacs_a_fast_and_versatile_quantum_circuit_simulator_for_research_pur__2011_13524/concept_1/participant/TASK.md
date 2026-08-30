# Structure-aware quantum circuit fusion

Improve the supplied compiler planner for repeated state-vector simulation. Produce
legal fused-block schedules that lower a deterministic roofline resource model,
without changing gate semantics or hiding expensive matrix construction.

`input/PROTOCOL.md` defines the interface and resource model. `workspace/model.py`
is the public checker/cost implementation; `baseline/solution.py` is a working
multi-schedule planner. `input/examples.json` contains representative circuits.

Deliver `solution.py` and any supporting files in the designated output directory.
Run it as `python3 solution.py INPUT_JSON OUTPUT_JSON`. It receives a batch of
circuits and returns their schedules. Only standard Python, NumPy and SciPy may
be assumed; no network, GPU, or other files are available.

The fixed target is geometric-mean modeled speedup **at least 1.20** over the
supplied baseline, with **every family at least 0.98**, and every schedule valid.
Private circuits cover modular, nearest-neighbor, wide-frontier, diagonal-heavy,
and shifting-locality structures within the published bounds. The complete batch
has a 180-second wall-clock limit, four CPU threads, and 4 GiB address space.
Scores report aggregate speedup, worst-family speedup, legality, and runtime.
The resource model is the objective, not a claim of measured Qulacs wall speed.
