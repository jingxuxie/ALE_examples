# Repair a DMFT integration adapter

Repair the numerical pipeline in the supplied runnable adapter: preserve fermionic transform conventions, update every antiferromagnetic band, and reconcile signed Legendre measurements with frequency observables.

Implement a standalone `attempt/solve.py` accepting `--input JSON --output JSON`. The complete interface is in `input/CONTRACT.md`; the starting implementation and historical excerpts are in `workspace/`. Matrix Fourier coverage is an explicitly defined extension, not a claim about a production cluster solver.

Python, NumPy, and SciPy are available. Each case has a 120-second limit. Accuracy is scored continuously and separately by scientific component. The two input samples have no answer labels.
