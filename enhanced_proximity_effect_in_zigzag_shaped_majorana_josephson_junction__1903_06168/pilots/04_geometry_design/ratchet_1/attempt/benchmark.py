import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import numpy as np
from physics import ForwardModel, feasibility
from fast_physics import Spectrum
from geometry import make_geometry

request = json.load(open('../participant/input/example.json'))
masks = make_geometry(request, None)
top = np.argmax(masks['sc_top'], axis=0)
bottom = request['grid']['ny'] - 1 - np.argmax(masks['sc_bottom'][::-1], axis=0)
print('BOUNDARIES', top.tolist(), bottom.tolist(), flush=True)
print('FEASIBILITY', feasibility(request, masks), flush=True)
for point in request['operating_points']:
    started = time.monotonic()
    model = ForwardModel(request, masks, point)
    spectrum = Spectrum(model)
    print('ENDPOINTS', point, spectrum.invariant(True), spectrum.values, time.monotonic()-started, flush=True)
    print('SCAN', spectrum.scan(9), spectrum.values, time.monotonic()-started, flush=True)
