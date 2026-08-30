import search
import evolve
import concurrent.futures
import json
import time

def main():
    lock = (search.ROOT / '.workers.lock').open('a')
    search.fcntl.flock(lock, search.fcntl.LOCK_EX)
    started = time.monotonic()
    random = search.np.random.default_rng(415026178)
    archive = []
    for path in sorted(search.ROOT.glob('evolution.round*.json')):
        archive.extend(json.loads(path.read_text())[:5])
    archive.extend(json.loads((search.ROOT / 'evolution.json').read_text())[:16])
    if (search.ROOT / 'broad_refined.json').exists():
        archive.extend(json.loads((search.ROOT / 'broad_refined.json').read_text())[:4])
    archive.sort(key=evolve.ranking, reverse=True)
    candidates = []
    for row in archive:
        fields = search.np.array(row['fields'])
        if all(search.np.sqrt(search.np.mean((fields-search.np.array(other))**2)) > .025 for other in candidates):
            candidates.append(fields.tolist())
        if len(candidates) == 32:
            break
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        results = evolve.run_batch(executor, candidates, random, 96)
        (search.ROOT / 'selection96.json').write_text(json.dumps(results, indent=2))
        print(json.dumps(dict(event='selection96', elapsed=time.monotonic()-started, best=results[0])), flush=True)
        results = evolve.run_batch(executor, [row['fields'] for row in results[:8]], random, 256)
        (search.ROOT / 'selection256.json').write_text(json.dumps(results, indent=2))
        print(json.dumps(dict(event='selection256', elapsed=time.monotonic()-started, best=results[0])), flush=True)
    best = results[0]
    witness = dict(schema_version=1, fields=best['fields'], orientation=best['orientation'])
    (search.ROOT / 'witness.json').write_text(json.dumps(witness, indent=2) + '\n')

if __name__ == '__main__':
    main()
