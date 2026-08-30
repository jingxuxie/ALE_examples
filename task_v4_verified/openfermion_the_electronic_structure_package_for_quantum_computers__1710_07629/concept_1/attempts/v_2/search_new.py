import time
import numpy as np
from champion.optimize import candidates, rotate, cost
from fast import refine
from polishing import polish
from charge_bases import charge_bases
from pair_search import pair_rotations


def alignment_rotations(factors, mode):
    dimension = factors.shape[1]
    choices = []
    for factor_index, factor in enumerate(factors):
        values, vectors = np.linalg.eigh(factor)
        order = np.argsort(-abs(values))
        principal = vectors[:, order[0]].copy()
        conflict = 1.0 - np.max(principal * principal)
        if mode == 2:
            if abs(values[order[1]]) < .06 * abs(values[order[0]]):
                continue
            vector = vectors[:, order[1]].copy()
        else:
            vector = principal
        pivot = np.argmax(abs(vector))
        if vector[pivot] < 0:
            vector = -vector
        if mode == 1:
            indices = np.argsort(-vector * vector)
            count = np.searchsorted(np.cumsum(vector[indices] ** 2), .97) + 1
            indices = indices[:max(2, count)]
            rotation = np.eye(dimension)
            rotation[np.ix_(indices, indices)] = np.linalg.eigh(factor[np.ix_(indices, indices)])[1]
        elif mode == 3:
            rotation = vectors
        elif mode == 4:
            cosine = vector[pivot]
            sine = np.sqrt(max(0.0, 1 - cosine * cosine))
            if sine < 1e-7:
                continue
            direction = vector.copy()
            direction[pivot] = 0.0
            direction /= sine
            axis = np.eye(dimension)[:, pivot]
            rotation = np.eye(dimension) + (cosine - 1) * (np.outer(direction, direction) + np.outer(axis, axis))
            rotation += sine * (np.outer(direction, axis) - np.outer(axis, direction))
        else:
            if mode == 5:
                pivot = np.argsort(-abs(vector))[1]
            direction = vector.copy()
            direction[pivot] -= 1.0
            squared_norm = direction @ direction
            if squared_norm < 1e-18:
                continue
            rotation = np.eye(dimension) - 2 * np.outer(direction, direction) / squared_norm
        choices.append((-conflict, factor_index, rotation))
    choices.sort(key=lambda entry: entry[0])
    return choices


def solve_case(case, seconds=9.0, verbose=False):
    started = time.monotonic()
    deadline = started + max(.01, seconds)
    search_deadline = deadline - min(.8, seconds * .12)
    one_body = np.asarray(case['one_body'], dtype=float)
    factors = np.asarray(case['factors'], dtype=float)
    initials = candidates(one_body, factors)
    best = initials[0]
    pool = []
    coarse_lows = {}
    first_stage_cache = {}

    def log(*items):
        if verbose:
            print(*items, 'elapsed', round(time.monotonic() - started, 3), flush=True)

    def remember(candidate):
        nonlocal best
        value = cost(*rotate(one_body, factors, candidate[1], candidate[2]))
        result = (value, candidate[1], candidate[2])
        if value < best[0]:
            best = result
        return result

    def trial(orbital, auxiliary, schedule, iterations, label):
        if time.monotonic() >= search_deadline:
            return
        first = refine(one_body, factors, orbital, auxiliary, schedule[:1], maxiter=iterations[:1], deadline=search_deadline)
        cache = first_stage_cache.setdefault(schedule[0], [])
        matched = False
        for entry in cache:
            previous = entry[0]
            if abs(first[0] - previous[0]) > 2e-5 * max(1.0, previous[0]):
                continue
            orbital_overlap = np.max(abs(first[1].T @ previous[1]), axis=0)
            auxiliary_overlap = np.max(abs(first[2] @ previous[2].T), axis=0)
            if np.min(orbital_overlap) > .99999 and np.min(auxiliary_overlap) > .99999:
                entry[1] += 1
                matched = True
                if entry[1] % 8:
                    log(*label, 'repeated basin')
                    return
                break
        if not matched:
            cache.append([first, 0])
        candidate = refine(one_body, factors, first[1], first[2], schedule[1:], maxiter=iterations[1:], deadline=search_deadline)
        coarse_value = candidate[0]
        previous_coarse = coarse_lows.get(schedule[-1], float('inf'))
        coarse_lows[schedule[-1]] = min(previous_coarse, coarse_value)
        promising = coarse_value < min(best[0] * 1.02, previous_coarse * .9998)
        if promising or coarse_value < best[0] * .9998:
            candidate = remember(candidate)
            candidate = refine(one_body, factors, candidate[1], candidate[2], [.0003, .00002],
                               maxiter=[350, 450], deadline=search_deadline)
            candidate = remember(candidate)
            if time.monotonic() < search_deadline:
                remember(polish(one_body, factors, candidate[1], candidate[2], sweeps=4, deadline=search_deadline))
        log(*label, coarse_value, 'best', best[0])

    for index, initial in enumerate(initials[:6]):
        if time.monotonic() > started + seconds * .20:
            break
        candidate = refine(one_body, factors, initial[1], initial[2], [.1, .025, .004],
                           maxiter=[250, 225, 275], deadline=search_deadline)
        candidate = remember(candidate)
        if not any(abs(candidate[0] - previous[0]) < .0005 * best[0] for previous in pool):
            pool.append(candidate)
        log('initial', index, candidate[0])
    pool.sort(key=lambda entry: entry[0])
    for candidate in pool[:2]:
        if time.monotonic() > started + seconds * .30:
            break
        candidate = refine(one_body, factors, candidate[1], candidate[2], [.0004, .00002],
                           maxiter=[350, 450], deadline=search_deadline)
        candidate = remember(candidate)
        if time.monotonic() < search_deadline:
            candidate = remember(polish(one_body, factors, candidate[1], candidate[2], sweeps=4, deadline=search_deadline))
        log('initial fine', candidate[0])

    random = np.random.default_rng(41902)
    for stage in (0, 'bases', 'pairs', 1, 2, 'bases', 5, 3, 4):
        if time.monotonic() >= search_deadline:
            break
        base = best
        rotated_body, rotated_factors = rotate(one_body, factors, base[1], base[2])
        if stage == 'bases':
            for index, rotation in enumerate(charge_bases(rotated_factors, random, count=12)):
                if time.monotonic() >= search_deadline:
                    break
                trial(base[1] @ rotation, base[2], [.025, .004, .0007], [200, 200, 300], ('basis', index))
        elif stage == 'pairs':
            for penalty, identifiers, rotation in pair_rotations(rotated_body, rotated_factors)[:12]:
                if time.monotonic() >= search_deadline:
                    break
                if penalty < .35:
                    trial(base[1] @ rotation, base[2], [.025, .004, .0007], [200, 200, 300], ('pair', identifiers))
        else:
            for _, factor_index, rotation in alignment_rotations(rotated_factors, stage):
                if time.monotonic() >= search_deadline:
                    break
                trial(base[1] @ rotation, base[2], [.05, .01, .002], [200, 200, 250], ('align', stage, factor_index))

    index = 0
    while time.monotonic() < search_deadline:
        base = best
        noise = random.normal(size=base[1].shape) * (.35 if index % 2 else .65) / np.sqrt(len(one_body))
        skew = noise - noise.T
        rotation = 2 * np.linalg.inv(np.eye(len(one_body)) - skew) - np.eye(len(one_body))
        trial(base[1] @ rotation, base[2], [.06, .012, .002], [200, 200, 250], ('random', index))
        index += 1

    if time.monotonic() < deadline - .12:
        candidate = refine(one_body, factors, best[1], best[2], [.00002, .000004, .0000008],
                           maxiter=[350, 500, 650], deadline=deadline - .12)
        remember(candidate)
    if time.monotonic() < deadline - .03:
        remember(polish(one_body, factors, best[1], best[2], sweeps=10, deadline=deadline - .03))
    log('best', best[0], 'ratio', best[0] / case['baseline_cost'])
    return best
