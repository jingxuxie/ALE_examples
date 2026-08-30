# Temperature-transferable collision-event compression

Compress mode-resolved electron-phonon scattering catalogues for repeated transport calculations. One sparse, nonnegative event reweighting must work over the entire supplied temperature range; preserving total scattering alone is insufficient.

Provided assets are development catalogues, their scoring model in `workspace/physics.py`, and a runnable importance-sampling baseline. These are reduced reciprocal Fermi-surface collision models, not raw EPW output. `input/SCHEMA.md` defines the interface and physical conventions.

Submit `solve.py` and any supporting files in your output directory. Invocation:

```
python3 solve.py --input INPUT_NPZ --output OUTPUT_NPZ
```

Return selected event indices and one nonnegative multiplier per event, within the input event budget. The same multiplier applies to every phonon branch and temperature. The evaluator scores preserved linewidths, low-order collision dissipation, and full conductivity tensors, including the worst scattering family. Hidden families cover forward scattering, weakly connected valleys, localized hot regions, and mixed energy scales.

The fixed improvement target is a mean score of at least **80/100** and a worst-family score of at least **70/100**, with every output valid. Each case permits 90 wall seconds, four numerical threads, and 4 GiB address space. No network or access outside supplied assets and your output is permitted. Numerical evaluation uses only your saved submission; prepare any trained assets in advance.
