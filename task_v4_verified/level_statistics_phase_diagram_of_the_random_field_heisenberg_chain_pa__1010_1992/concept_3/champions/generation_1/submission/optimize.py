from search import *

def mutation(random, parent, generation):
    fields = np.array(parent['fields'])
    mode = random.random()
    if mode < 0.08:
        fields = np.roll(fields, int(random.integers(12)))
        if random.random() < 0.5:
            fields = fields[::-1]
        if random.random() < 0.5:
            fields = -fields
    else:
        step = float(random.choice([0.004, 0.009, 0.02, 0.045, 0.09, 0.18, 0.36], p=[0.06, 0.12, 0.22, 0.26, 0.20, 0.10, 0.04]))
        if mode < 0.20:
            fields *= 1 + random.normal(0, step / 3)
        elif mode < 0.48:
            selected = random.choice(12, int(random.integers(1, 4)), replace=False)
            fields[selected] += random.normal(0, step, len(selected))
        else:
            fields += random.normal(0, step, 12)
    fields -= fields.mean()
    if not valid(fields):
        return None
    return dict(fields=fields.tolist(), orientation=parent['orientation'], kind=parent.get('kind', -1))

def evaluate(candidate):
    statistics = proxy_statistics(spectrum(candidate['fields']))
    candidate['base'] = candidate['orientation'] * statistics['difference']
    if candidate['base'] < 0.035:
        return None
    return full_measure(candidate)

def choose_elites(candidates, count):
    candidates.sort(key=lambda item:item['score'], reverse=True)
    chosen = []
    for candidate in candidates:
        fields = np.array(candidate['fields'])
        if all(np.sqrt(np.mean((fields - np.array(other['fields'])) ** 2)) > 0.035 for other in chosen):
            chosen.append(candidate)
        if len(chosen) == count:
            break
    return chosen

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('finalists.json'))
    parser.add_argument('--seed', type=int, default=998101)
    parser.add_argument('--seconds', type=float, default=1200)
    parser.add_argument('--batch', type=int, default=96)
    parser.add_argument('--elites', type=int, default=16)
    args = parser.parse_args()
    random = np.random.default_rng(args.seed)
    elites = choose_elites(json.loads(args.input.read_text()), args.elites)
    best = elites[0]
    start = time.monotonic()
    print('initial', best, flush=True)
    generation = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        while time.monotonic() - start < args.seconds:
            candidates = []
            while len(candidates) < args.batch:
                if random.random() < 0.35:
                    parent = best
                else:
                    parent = elites[int(random.integers(len(elites)))]
                candidate = mutation(random, parent, generation)
                if candidate is not None:
                    candidates.append(candidate)
            results = []
            for result in executor.map(evaluate, candidates):
                if result is None:
                    continue
                candidate, report = result
                results.append(candidate)
                if candidate['score'] > best['score']:
                    best = candidate
                    save_result(candidate, report, Path('.'), 'witness')
                    print('BEST', json.dumps({key:value for key,value in candidate.items() if key != 'fields'}), 'generation', generation, 'seconds', time.monotonic()-start, flush=True)
                if candidate['passed']:
                    save_result(candidate, report, Path('.'), 'passing')
                    print('PASS', candidate['margin'], candidate['core'], flush=True)
                    (Path('optimized.json')).write_text(json.dumps(choose_elites(elites+results, args.elites), indent=2))
                    return
            elites = choose_elites(elites + results, args.elites)
            generation += 1
            Path('optimized.json').write_text(json.dumps(elites, indent=2))
            print('generation', generation, 'valid', len(results), 'best', best['score'], best['core'], 'seconds', time.monotonic()-start, flush=True)
    print('complete', time.monotonic()-start, flush=True)

if __name__ == '__main__':
    main()
