import time

import numpy as np

from .contract import encode, order_key, orders_for
from .infrared import massless_coefficients
from .massive import massive_coefficients


def evaluate(integral, settings):
    started = time.perf_counter()
    if all(mass == 0 for mass in integral["masses2"]):
        values, work, error, strategy = massless_coefficients(integral)
    else:
        if min(integral["masses2"]) <= 0:
            raise ValueError("Mixed massive/massless topologies are outside the release domain")
        values, work, error, strategy = massive_coefficients(integral, settings)
    if not np.all(np.isfinite(values)):
        raise ArithmeticError("Nonfinite coefficient; no unchecked replacement is permitted")
    return {"coefficients": {order_key(order): encode(value)
                             for order, value in zip(orders_for(integral), values)},
            "seconds": time.perf_counter() - started, "work": int(work),
            "estimated_error": float(error), "strategy": strategy,
            "converged": "UNCONVERGED" not in strategy}
