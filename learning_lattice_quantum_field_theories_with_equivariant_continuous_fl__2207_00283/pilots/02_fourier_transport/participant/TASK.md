# Fourier-density transport

Implement a NumPy/SciPy-compatible extension for real lattice fields providing
independent-mode Fourier packing and reconstruction, spectral forward/inverse
transport, log-density accounting, sensitivities, symmetry diagnostics, and
physical momenta.

Provide `workspace/solve.py` that reads one NPZ archive and writes the
contracted output arrays:

```
python solve.py INPUT.npz OUTPUT.npz
```

`input/CONTRACT.md` specifies every input, output, convention, execution limit,
and scoring rule. Two small unlabeled archives illustrate the interface; they
are not a training set. Use only participant-visible files and the supplied
dependency runtime at `input/runtime/bin/python3.12`. Support the documented
batch, channel, and spatial layouts without hard-coded cases.
