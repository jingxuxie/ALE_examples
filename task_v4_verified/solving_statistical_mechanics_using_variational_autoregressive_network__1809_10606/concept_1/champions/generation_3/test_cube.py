import time
import numpy as np
from cube import linear_logits, linear_moments, quadratic_moments
from regional import configurations

rng = np.random.default_rng(91)
for count in [0, 1, 4, 10, 19]:
    design = np.column_stack((np.ones(1 << count), configurations(count)))
    parameters = rng.normal(size=count + 1)
    values = rng.uniform(size=1 << count)
    start = time.monotonic()
    logits = linear_logits(parameters)
    moments = linear_moments(values)
    quadratic = quadratic_moments(values)
    elapsed = time.monotonic() - start
    errors = [np.max(abs(logits - design @ parameters)),
              np.max(abs(moments - design.T @ values)),
              np.max(abs(quadratic - design.T @ (values[:, None] * design)))]
    print(count, 'errors', errors, 'time', elapsed, flush=True)
    assert np.allclose(logits, design @ parameters, rtol=1e-10, atol=1e-10)
    assert np.allclose(moments, design.T @ values, rtol=1e-10, atol=1e-8)
    assert np.allclose(quadratic, design.T @ (values[:, None] * design), rtol=1e-10, atol=1e-8)
