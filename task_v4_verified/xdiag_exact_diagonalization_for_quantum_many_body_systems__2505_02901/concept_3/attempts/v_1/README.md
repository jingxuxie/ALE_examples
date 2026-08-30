# Spin-register spectroscopy controller

Run `python3 solve.py`. The controller reads and writes the specified
newline-delimited JSON protocol. It requires only Python, NumPy, and SciPy;
it does not import the participant simulator or read any external data files.

The implementation uses exact evolution in the twenty-dimensional conserved
sector, analytic Hamiltonian-propagator derivatives, and bounded multinomial
maximum-likelihood estimation. Nine initial experiments establish the model;
the remaining experiments adaptively minimize the trace of the inverse Fisher
information, including the option of direct detector calibration. Multiple
optimization starts address possible initial local minima.

All numerical thread pools are limited to one thread. The controller uses at
most the query budget supplied at startup and returns all twenty parameters
within their public bounds.
