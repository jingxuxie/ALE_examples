from optimize import *
from turnover import simplify, search


for instance in INSTANCES:
    improved = []
    for path in list(Path('.').glob(instance['id'] + '_*.json')):
        if 'compressed' in path.name:
            continue
        try:
            circuit = json.loads(path.read_text())
            if not isinstance(circuit, dict) or set(circuit) != {'id', 'layers'} or circuit['id'] != instance['id']:
                continue
            edges, parameters = unpack(circuit)
            if len(edges) > instance['budgets']['max_gates'] + 15:
                continue
            error = np.linalg.norm(Fit(instance, edges).evaluate(parameters.ravel())[0]) * np.sqrt(2)
            if error > 1e-8:
                continue
            gates = [(gate['u'], gate['v'], gate['theta'], gate['phi']) for layer in circuit['layers'] for gate in layer]
            output = simplify(gates, instance)
            layers = schedule(output, instance['n_modes'])
            if len(output) < len(gates) or len(layers) < len(circuit['layers']):
                source = path.stem[len(instance['id']) + 1:] + '_compressed'
                Path(instance['id'] + '_' + source + '.json').write_text(json.dumps(dict(id=instance['id'], layers=layers)))
                print('COMPRESSED', instance['id'], path.name, len(gates), len(output), len(layers), flush=True)
                improved.append((len(output), len(layers), source))
        except (ValueError, KeyError, TypeError):
            continue
    for count, depth, source in sorted(improved)[:4]:
        search(instance, source=source, width=60, iterations=100)
