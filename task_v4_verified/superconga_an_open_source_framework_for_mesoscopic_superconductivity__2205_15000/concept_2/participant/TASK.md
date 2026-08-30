# Pattern a mesoscopic superconducting spectrometer

Construct a manufacturable metallic-inclusion pattern whose local Andreev
spectra realize the supplied fingerprint across three operating conditions.
The supplied spin-singlet, prescribed-gap BdG device is a microscopic design
surrogate inspired by SuperConga's mesoscopic geometry and spectroscopy work;
it is not a self-consistent quasiclassical calculation.

Assets: `input/device.json`, target spectra, the complete forward model in
`workspace/spectral.py`, and a runnable baseline. The fabrication and numerical
contract is in `input/INTERFACE.md`.

Write `design.json` in your output directory, containing `{"pattern": [...]}`.
Any pattern meeting the constraints is accepted; no particular pattern is
required. It must use the specified normal-material budget, preserve connected
superconducting material, achieve core score at least **0.96**, and worst
operating-condition score at least **0.94**. Scores measure normalized spectral
fidelity. All target conditions are public.

You have one hour of development, CPU only, no external services. The final
artifact is at most 64 KiB; verification has a 120-second CPU budget and 4 GiB
memory. No report or source-code submission is required beyond the artifact.
