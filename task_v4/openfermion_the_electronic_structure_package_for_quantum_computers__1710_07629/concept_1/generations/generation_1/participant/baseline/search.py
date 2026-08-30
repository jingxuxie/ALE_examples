import time
import numpy as np
from optimize import candidates, cost, rotate, refine
from native import polish


def solve_case(case, seconds=8.5, verbose=False):
    started = time.monotonic()
    deadline = started + seconds
    one_body = np.asarray(case['one_body'], dtype=float)
    factors = np.asarray(case['factors'], dtype=float)
    initials = candidates(one_body, factors)
    best = initials[0]
    pool = []

    def log(*items):
        if verbose:
            print(*items, 'elapsed', round(time.monotonic()-started, 3), flush=True)

    def remember(candidate):
        nonlocal best
        value = cost(*rotate(one_body, factors, candidate[1], candidate[2]))
        candidate = (value, candidate[1], candidate[2])
        if value < best[0]:
            best = candidate
        return candidate

    for count, initial in enumerate(initials[:6]):
        if time.monotonic() > started + seconds * .58:
            break
        candidate = refine(one_body, factors, initial[1], initial[2], [.1, .025, .004],
                           maxiter=[250, 225, 275], deadline=min(deadline, started + seconds * .65))
        candidate = remember(candidate)
        if time.monotonic() < deadline - .25:
            candidate = remember(polish(one_body, factors, candidate[1], candidate[2], sweeps=4, deadline=deadline))
        if not any(abs(candidate[0] - previous[0]) < .0005 * best[0] for previous in pool):
            pool.append(candidate)
        log('coarse', count, candidate[0])

    pool.sort(key=lambda candidate: candidate[0])
    for candidate in pool[:3]:
        if time.monotonic() > started + seconds * .8:
            break
        if candidate[0] > best[0] * 1.08:
            continue
        refined = refine(one_body, factors, candidate[1], candidate[2], [.0007, .00007],
                         maxiter=400, deadline=min(deadline, started + seconds * .88))
        refined = remember(refined)
        if time.monotonic() < deadline - .25:
            refined = remember(polish(one_body, factors, refined[1], refined[2], sweeps=8, deadline=deadline))
        log('fine', refined[0])

    for smoothing in (.35, .8, .04):
        if time.monotonic() > deadline - 1.0:
            break
        refined = refine(one_body, factors, best[1], best[2], [smoothing, smoothing * .2, .005, .0005],
                         maxiter=[250, 200, 250, 350], deadline=deadline - .2)
        refined = remember(refined)
        if time.monotonic() < deadline - .25:
            refined = remember(polish(one_body, factors, refined[1], refined[2], sweeps=8, deadline=deadline))
        log('anneal', smoothing, refined[0])

    if time.monotonic() < deadline - .3:
        refined = refine(one_body, factors, best[1], best[2], [.00001], maxiter=500, deadline=deadline - .15)
        refined = remember(refined)
        if time.monotonic() < deadline - .15:
            remember(polish(one_body, factors, refined[1], refined[2], sweeps=3, deadline=deadline))
    log('best', best[0], 'ratio', best[0]/case['baseline_cost'])
    return best
