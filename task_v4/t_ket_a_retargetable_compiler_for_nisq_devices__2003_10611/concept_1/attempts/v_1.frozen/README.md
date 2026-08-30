# Calibration-weighted qubit routing

Run the submission with:

```sh
python3 solve.py < instance.json > route.json
```

`solve.py` reads the specified JSON contract and calls the included native
`router.so` library in-process through Python's standard `ctypes` interface.
The solver uses only these submitted files and the standard
system runtime. It does not load example routes, instance IDs, architecture
family labels, external packages, or quantum compiler libraries.

The complete native source is in `router.cpp`. If the library is missing or
cannot load on the current platform, the Python entry point rebuilds it with
the system C++17 compiler. Compilation time is deducted from the search budget.

## Search

- Pair-state shortest-path distances estimate calibrated movement to an
  executable edge, using several calibration and gate-cost weightings.
- Dependency-aware lookahead routing maintains the fixed initial permutation
  and executes only ready, physically adjacent logical gates.
- Beam search explores complete routing moves along alternative paths, moving
  either or both operands and retaining diverse intermediate placements.
- Multiple independent search trajectories refine valid prefixes, using
  randomized lookahead and annealed acceptance while retaining the best legal
  complete route.
- A final simplifier removes redundant routing SWAPs only when all affected
  logical gates remain physically executable. It never removes logical gates.

Every candidate's score includes calibrated gate/SWAP work and the exact physical
two-qubit depth. The final permutation is unrestricted, as specified. Search is
single-threaded and normally uses a four-second wall-clock budget shared between
the Python entry point and native search. Startup and compilation delays reduce
the available search time, leaving headroom under the eight-second invocation
limit. Search phases also check deadlines while expanding candidates.

## Validation

`validation.json` records the final constrained 36-case run: all 12 supplied
public instances plus 24 independently generated cases, six cases per family.
Each invocation is constrained to one CPU, a 2-GiB address-space limit, and an
eight-second CPU limit, with a 7.8-second external timeout. The report includes
exact validator results, public and mixed-suite cost reductions, memory usage,
and elapsed times. Generated cases are development tests, not hidden tests.

The recorded public geometric-mean cost reduction is **23.49%**, with **15.82%**
in the weakest public architecture family. All 36 constrained cases are valid;
the suite takes **166.21 seconds**, with a **5.03-second** maximum invocation.
The mixed-suite reduction is **23.64%**. These measurements use the submitted
in-process runner and the exact supplied route validator.

Additional development checks cover 36 generated workloads, 160 randomized
architecture/program combinations, and 80 AddressSanitizer/UndefinedBehaviorSanitizer
cases. These include maximum dimensions, dense graphs, extreme edge weights,
repeated opaque gates, hub traffic, and randomized gate orientations.

`bench.py`, `stress.py`, `fuzz.py`, and `audit.py` are development harnesses that
use the original participant directory's exact validator. They are not loaded
by the submission entry point.

`deadline_test.py` verifies that an injected startup delay consumes the shared
budget instead of restarting a full native search. Library rebuilds use an
atomic replacement so another invocation cannot load a partially written file.

To rebuild the native executable explicitly:

```sh
g++ -O3 -std=c++17 -shared -fPIC router.cpp -o router.so
```
