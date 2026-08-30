# Stationary tomography baseline

`predict.py` pools the single-gate calibration counts across time and estimates
five affine Bloch maps independently for each device. It composes those maps for
each query, using the disclosed preparation and readout calibration. A conservative
singular-value contraction prevents amplified finite-shot instabilities.

This intentionally weak baseline does not model persistent environmental branches,
pulse history, or acquisition-time drift. It uses NumPy only and has no private
imports. Run it from the participant directory as described in `TASK.md`.
