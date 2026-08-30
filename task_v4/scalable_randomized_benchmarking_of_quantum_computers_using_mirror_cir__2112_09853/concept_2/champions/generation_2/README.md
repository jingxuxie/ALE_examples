# Active mirror benchmarking policy

Run `python -B policy.py`. The policy speaks the specified JSON-lines protocol
and uses only the greeting and subsequent experiment observations.

The acquisition combines singleton controls, depth-zero SPAM probes, dense
random matchings, and adaptive dense/pair probes. A discretized spike-and-slab
posterior estimates positive crosstalk, bounded base rates, and matching-dependent
SPAM. Smooth temporal nuisance terms handle the drift family. Posterior target
covariances guide acquisition; final predictions minimize posterior expected
normalized squared error.

`sampler.so` is the included native sampling helper, loaded through `ctypes`.
Its source is `sampler.cpp`; no compilation is needed during evaluation.
The reproducible build command is:

```
g++ -O3 -std=c++17 -shared -fPIC sampler.cpp -o sampler.so
```

The only Python dependency is NumPy. The policy does not read development data,
use the network, or write to its submission directory.
