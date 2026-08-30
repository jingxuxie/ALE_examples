from minor_search import *


def main():
    started = time.monotonic()
    base = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=np.int8)
    updates = update_matrices(base)
    arcs = [np.full(16, -1, dtype=np.int8), np.ones(16, dtype=np.int8)]
    for start in range(16):
        for length in range(1, 16):
            arcs.append(np.where((np.arange(16) - start) % 16 < length, 1, -1).astype(np.int8))
    arcs = np.array(arcs)
    mutations = np.full((16, len(arcs), 16), -1, dtype=np.int64)
    sizes = np.empty((16, len(arcs)), dtype=int)
    ordering = []
    for site in range(16):
        candidates = np.broadcast_to(base, (len(arcs), 16, 16)).copy()
        candidates[:, :, site] = arcs
        scores = evaluate(candidates)[0]
        for variant, arc in enumerate(arcs):
            changed = np.flatnonzero(arc != base[:, site]) * 16 + site
            mutations[site, variant, :len(changed)] = changed
            sizes[site, variant] = len(changed)
        ordering.append(np.argsort(scores + np.random.default_rng(site).uniform(0, 1e-10, len(scores))))
    ordering = np.array(ordering)
    tested = 0

    def test_padded(padded):
        nonlocal tested
        counts = (padded >= 0).sum(axis=1)
        for count in np.unique(counts):
            if count == 0:
                continue
            group = padded[counts == count]
            selected_all = group[group >= 0].reshape(len(group), count)
            for start in range(0, len(group), 4096):
                selected = selected_all[start:start + 4096]
                minors = updates[:, selected[:, :, None], selected[:, None, :]]
                signs = np.linalg.slogdet(minors)[0].prod(axis=0)
                for selected_indices in selected[signs < 0]:
                    candidate = base.copy()
                    candidate.reshape(-1)[selected_indices] *= -1
                    if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                        save(candidate, 'found_worldlines.json')
                        save(candidate, 'witness.json')
                        print('FOUND', selected_indices.tolist(), tested, round(time.monotonic() - started, 1), flush=True)
                        return True
                tested += len(selected)
                if time.monotonic() - started > 650:
                    raise TimeoutError
        return False

    all_masks = (np.arange(65536)[:, None] >> np.arange(16)[None]) & 1
    for site in range(16):
        padded = np.where(all_masks, np.arange(16)[None] * 16 + site, -1)
        if test_padded(padded):
            return
    print('All single worldlines', tested, round(time.monotonic() - started, 1), flush=True)
    for count, choices in [(2, 242), (3, 16), (4, 8), (3, 32), (4, 12)]:
        grid = np.indices((choices,) * count).reshape(count, -1).T
        for site_index, sites in enumerate(combinations(range(16), count)):
            padded = np.concatenate([mutations[site, ordering[site, grid[:, position]]] for position, site in enumerate(sites)], axis=1)
            if test_padded(padded):
                return
            if site_index % 50 == 0:
                print('Progress', count, choices, site_index, tested, round(time.monotonic() - started, 1), flush=True)
        print('Stage', count, choices, tested, round(time.monotonic() - started, 1), flush=True)


if __name__ == '__main__':
    try:
        main()
    except TimeoutError:
        print('Time limit', flush=True)
