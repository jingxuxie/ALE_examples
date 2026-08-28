# Local protection compiler

Implement `solver.py` with `solve(case: dict) -> dict`. Compile the supplied
local error operators into all reachable departures from the target gauge
sector, then choose bounded, quantized protection coefficients for both an
analog schedule and a repeated digital kick.

Return the sector-transfer certificate and both control schedules in the format
specified by `input/protocol.md`. The protocol defines every operator, basis,
boundary convention, hardware constraint, and scoring quantity. Screening inputs
are in `input/screening/`. Use `workspace/` for scratch work.

Each call has 60 seconds on one CPU. Python, NumPy, and SciPy are available;
network access and private evaluation files are not. Cases are independent and
can have up to 160 matter sites. Full-system Hilbert enumeration is not viable.

Certificate accuracy, analog robustness, and digital robustness are evaluated
independently and combined geometrically. Both average and worst-family results
matter. A good analog vector need not be a good digital vector.
