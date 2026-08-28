from build_local import generate

for index, probability in enumerate([0.001, 0.002, 0.003, 0.004]):
    generate('calibration', 'hgp', 61000 + index, 64, 96, probability)
for index, probability in enumerate([0.025, 0.035, 0.045]):
    generate('calibration', 'high_rate', 62000 + index, 256, 400, probability)
for index, probability in enumerate([0.001, 0.002]):
    generate('calibration', 'circuit_surface', 63000 + index, 128, 13, probability)
