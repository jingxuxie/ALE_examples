# Active mirror-benchmark policy

Run `python -B policy.py`. The policy consumes the JSON-lines protocol on stdin
and emits only protocol responses on stdout.

The policy uses the disclosed graph and family priors, exact binomial shot
likelihoods, sparse interaction inference, context-dependent SPAM parameters,
and sinusoidal drift inference. Experimental matchings and even depths are
selected using posterior expected reduction in the normalized prediction loss.
Final inference uses tempered-chain exchanges to improve exploration of sparse
interaction configurations. Shot, matching-size, and runtime budgets are bounded.

`sampler.so` supplies the acquisition sampler; `core.so` supplies the final
sampler with support exchanges and coupled base/interactions. Rebuild them with:

```
g++ -O3 -std=c++11 -DIMPROVED_PRIOR -DTEMPERED -fPIC -shared sampler.cpp -o core.so
g++ -O3 -std=c++11 -fPIC -shared sampler.cpp -o sampler.so
```

Runtime dependencies are Python and NumPy; no external assets or network are used.
