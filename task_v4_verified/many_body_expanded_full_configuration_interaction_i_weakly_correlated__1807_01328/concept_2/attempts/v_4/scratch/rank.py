from robust import *

engine = Engine()
records = []
for pattern in sys.argv[1:] or ['block_*.json', 'match_*.json', 'star_*.json', 'trial_*.json', 'fullfit_*.json', 'vvfit_*.json']:
    for path in sorted(Path('.').glob(pattern)):
        controls = coefficients(model.load_witness(path))[CONTROL]
        info = engine.summary(controls)
        parent = info['parent']
        tail = abs(info['tail'])
        if tail < 45 or parent > 2 or info['physical'][0] < .95 or info['physical'][1] < .4:
            continue
        likelihood = probability(engine, controls, count=2048)
        nominal = min(1, 1/max(parent, .0001), tail/50, tail/(100*max(parent, .0001)))
        score = nominal + min(1, likelihood['vv']['success']/.95) + min(1, likelihood['full']['success']/.95)
        records.append(dict(path=str(path), score=score, nominal=nominal, **info, probability=likelihood))
records.sort(key=lambda record: record['score'], reverse=True)
Path('catalog.json').write_text(json.dumps(records, indent=2))
for record in records[:15]:
    print(record, flush=True)
for index, record in enumerate(records[:40]):
    save('catalog_%02d.json' % index, coefficients(model.load_witness(record['path']))[CONTROL])
if records:
    save('witness.json', coefficients(model.load_witness(records[0]['path']))[CONTROL])
