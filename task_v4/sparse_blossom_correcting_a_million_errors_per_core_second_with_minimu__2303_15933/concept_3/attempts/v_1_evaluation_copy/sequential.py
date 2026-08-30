import numpy as np

from solution import Model, design


def solve(spec, query, pilot=50, intermediate=12000, criterion='rms', diagnostics=None, early=2000):
    model = Model(spec)
    action_count = len(spec['actions'])
    counts = np.zeros((action_count, model.state_count), dtype=np.int64)
    used = np.zeros(action_count, dtype=int)
    queries = 0
    budget = spec['shot_budget']

    def sample(action, shots):
        nonlocal queries
        while shots:
            batch = min(int(shots), spec['max_shots_per_query'])
            counts[action] += query(int(action), batch)
            used[action] += batch
            queries += 1
            shots -= batch

    for action in range(1, action_count):
        exposures = model.exposures[action, 0]
        if exposures.max() < 3 * exposures.min():
            continue
        ordered = np.sort(exposures)
        if ordered[-2] < 0.3 and abs(ordered[-1] - 120) > 1:
            continue
        sample(action, pilot)
    fitted = model.fit(counts)
    stages = [early, 6000, intermediate, budget]
    for phase, desired in enumerate(stages):
        allocation, information = design(model, fitted, used, budget, criterion)
        remaining = budget - int(used.sum())
        phase_budget = min(desired, remaining)
        last = phase == len(stages) - 1
        active = np.flatnonzero(allocation * phase_budget >= (30 if last else 70))
        if len(active) == 0:
            active = np.array([np.argmax(allocation)])
        available = spec['max_queries'] - queries
        max_active = max(1, available - (phase_budget + spec['max_shots_per_query'] - 1) // spec['max_shots_per_query'])
        if not last:
            max_active = min(max_active, max(1, (available - 10) // (len(stages) - phase)))
        if len(active) > max_active:
            active = np.argsort(allocation)[-max_active:]
        target = phase_budget * allocation[active] / allocation[active].sum()
        shots = np.floor(target).astype(int)
        remainder = phase_budget - int(shots.sum())
        if remainder:
            shots[np.argsort(target - shots)[-remainder:]] += 1
        for action, batch in zip(active, shots):
            if batch:
                sample(action, int(batch))
        fitted = model.fit(counts, fitted)
    if diagnostics is not None:
        diagnostics.update(used=used.tolist(), queries=queries,
                           predicted=np.sqrt(model.family_weights @ np.linalg.inv(
                               np.einsum('a,akl->kl', used, model.fisher(fitted))).diagonal()).tolist())
    return np.exp(fitted)
