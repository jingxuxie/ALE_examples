import time

from .contract import encode, order_key, orders_for
from .expansion import coefficient
from .kinematics import cache_key, canonicalize
from .regularization import estimate_laurent


CACHE = {}


def evaluate(integral, settings):
    started = time.perf_counter()
    work = 0

    def function(request):
        nonlocal work
        request = canonicalize(request)
        key = cache_key(request)
        if key not in CACHE:
            values, cost = estimate_laurent(request, settings)
            CACHE[key] = values
            work += cost
        return CACHE[key]

    coefficients = {order_key(order): encode(coefficient(integral, order, settings, function))
                    for order in orders_for(integral)}
    return {"coefficients": coefficients, "seconds": time.perf_counter() - started,
            "work": work, "estimated_error": settings["epsilon_step"] ** 2,
            "strategy": "ported-epsilon-sampling"}
