from .contract import arrays


def canonicalize(integral):
    result = dict(integral)
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    ordering = masses.argsort()
    result["masses2"] = masses[ordering].tolist()
    result["invariants"] = invariants[ordering][:, ordering].tolist()
    result["weights"] = weights[ordering].tolist()
    return result


def cache_key(integral):
    return str((integral["masses2"], integral["invariants"], integral.get("mu2", 1)))
