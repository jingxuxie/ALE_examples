import json
import math
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parent
expected = np.asarray(json.loads((root.parent.parent / 'participant/input/target.json').read_text())['cyclic_autocorrelation'])
fold4 = expected.reshape(-1, 4).sum(axis=0)
fold8 = expected.reshape(-1, 8).sum(axis=0)
spectrum4 = np.rint(np.fft.rfft(fold4).real).astype(int)
alternating = math.isqrt(int(spectrum4[2]))
radius4 = int(spectrum4[1])
norm = int(fold8[0] - fold8[4])
product = int(fold8[1] - fold8[3])
print('LOW DATA', spectrum4, norm, product, flush=True)
solutions = set()
for sign in [-1, 1]:
    even = (1024 + sign * alternating) // 2
    odd = 1024 - even
    for difference_even in range(-math.isqrt(radius4), math.isqrt(radius4) + 1):
        remainder = radius4 - difference_even ** 2
        difference_odd_abs = math.isqrt(remainder)
        if difference_odd_abs ** 2 != remainder:
            continue
        for difference_odd in set([-difference_odd_abs, difference_odd_abs]):
            if (even + difference_even) % 2 or (odd + difference_odd) % 2:
                continue
            lower = np.array([(even + difference_even) // 2, (odd + difference_odd) // 2, (even - difference_even) // 2, (odd - difference_odd) // 2])
            radius = math.isqrt(norm)
            for delta0 in range(-radius, radius + 1):
                if (delta0 - lower[0]) % 2:
                    continue
                for delta2 in range(-radius, radius + 1):
                    if (delta2 - lower[2]) % 2:
                        continue
                    remainder = norm - delta0 ** 2 - delta2 ** 2
                    if remainder < 0:
                        continue
                    horizontal = delta0 + delta2
                    vertical = delta0 - delta2
                    denominator = horizontal ** 2 + vertical ** 2
                    discriminant = denominator * remainder - product ** 2
                    if discriminant < 0 or denominator == 0:
                        continue
                    root_discriminant = math.isqrt(discriminant)
                    if root_discriminant ** 2 != discriminant:
                        continue
                    for side in [-1, 1]:
                        numerator1 = product * horizontal + side * vertical * root_discriminant
                        numerator3 = -product * vertical + side * horizontal * root_discriminant
                        if numerator1 % denominator or numerator3 % denominator:
                            continue
                        delta1 = numerator1 // denominator
                        delta3 = numerator3 // denominator
                        delta = np.array([delta0, delta1, delta2, delta3])
                        if np.any((delta + lower) % 2):
                            continue
                        candidate = np.r_[(lower + delta) // 2, (lower - delta) // 2]
                        actual = np.rint(np.fft.irfft(abs(np.fft.rfft(candidate)) ** 2)).astype(int)
                        if np.array_equal(actual, fold8):
                            canonical = min(tuple(np.roll(candidate, offset)) for offset in range(8))
                            reverse = min(tuple(np.roll(candidate[::-1], offset)) for offset in range(8))
                            solutions.add(min(canonical, reverse))
print('SOLUTIONS', len(solutions), sorted(solutions), flush=True)
np.save(root / 'fold8_candidates.npy', np.array(sorted(solutions)))
