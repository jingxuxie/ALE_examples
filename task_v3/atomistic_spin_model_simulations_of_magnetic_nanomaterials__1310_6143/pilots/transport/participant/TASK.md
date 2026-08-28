# Multisublattice transport

Implement `solve.py` so `python solve.py CASE.json OUTPUT.json` predicts the electrical response and atom-resolved spin-transfer response of the supplied magnetic stacks.

The full physical convention, units, array ordering, and output schema are in `input/FORMAT.md`. A runnable cell-averaged starting point and an older single-channel source excerpt are in `workspace/`; they are deliberately insufficient for resolved channels.

Cases include compensated and noncollinear order, missing interior sublattices, unequal moments, heterogeneous interfaces, and either current direction. Return resistance, channel currents, atomic effective fields, and instantaneous spin derivatives. All outputs must be finite and in the original atom/cell order.

Use only the case input and your submission files. Do not access authoring, reference, or evaluator files. The evaluator launches a new isolated process per case. Accuracy is scored continuously against a calibrated weak baseline, with mean-family and worst-family results and runtime reported separately.

Place all necessary submission files in the attempt directory. No external downloads are available during evaluation.
