import sys
from benchmark import cases, run

for request in cases():
    run(request, initialization='cat', pair_sweeps=2)
