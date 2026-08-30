import itertools
import json
import runpy
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT / '../../participant'
SPEC = json.loads((PARTICIPANT / 'input/spec.json').read_text())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f'Duplicate key: {key}'
        result[key] = value
    return result


def propagate(xbits, zbits, layers, inverse):
    for layer in reversed(layers) if inverse else layers:
        if inverse:
            for control, target in reversed(layer['cx']):
                if xbits & (1 << control):
                    xbits ^= 1 << target
                if zbits & (1 << target):
                    zbits ^= 1 << control
        for site, word in enumerate(layer['local']):
            for gate in reversed(word) if inverse else word:
                if gate == 'H':
                    if bool(xbits & (1 << site)) != bool(zbits & (1 << site)):
                        xbits ^= 1 << site
                        zbits ^= 1 << site
                elif gate == 'S':
                    if xbits & (1 << site):
                        zbits ^= 1 << site
        if not inverse:
            for control, target in layer['cx']:
                if xbits & (1 << control):
                    xbits ^= 1 << target
                if zbits & (1 << target):
                    zbits ^= 1 << control
    return xbits, zbits


def pauli(site, axis):
    return ((1 << site) if axis in 'XY' else 0,
            (1 << site) if axis in 'YZ' else 0)


def summarize(samples, minimum_target, mean_target, qubits):
    total = sum(samples)
    count = len(samples)
    minimum = min(samples)
    passed = minimum >= minimum_target and 1000 * total >= mean_target * count
    return {
        'count': count,
        'minimum': minimum,
        'weight_sum': total,
        'mean': total / count,
        'histogram': [samples.count(weight) for weight in range(qubits + 1)],
        'minimum_target': minimum_target,
        'mean_target_milli': mean_target,
        'mean_integer_margin': 1000 * total - mean_target * count,
        'passed': passed,
    }


def validate(path):
    file_stat = path.lstat()
    assert stat.S_ISREG(file_stat.st_mode) and file_stat.st_nlink == 1
    assert file_stat.st_size <= SPEC['artifact_max_bytes']
    artifact = json.loads(path.read_text(), object_pairs_hook=unique_object)
    assert set(artifact) == {'schema_version', 'circuits'}
    assert type(artifact['schema_version']) is int and artifact['schema_version'] == 1
    assert type(artifact['circuits']) is list
    families = {family['id']: family for family in SPEC['families']}
    assert len(artifact['circuits']) == len(families)
    seen = set()
    report = {'valid': True, 'passed': True, 'core_score': 1.0, 'families': {}}
    baseline = runpy.run_path(str(PARTICIPANT / 'baseline/solve.py'))
    for circuit in artifact['circuits']:
        assert set(circuit) == {'family', 'layers'}
        name = circuit['family']
        assert type(name) is str and name in families and name not in seen
        seen.add(name)
        family = families[name]
        qubits = family['n']
        targets = family['targets']
        layers = circuit['layers']
        assert type(layers) is list and len(layers) <= family['max_rounds']
        native_edges = {tuple(sorted(edge)) for edge in family['edges']}
        total_cx = 0
        for layer in layers:
            assert set(layer) == {'local', 'cx'}
            assert type(layer['local']) is list and len(layer['local']) == qubits
            assert all(type(word) is str and word in SPEC['allowed_local_words']
                       for word in layer['local'])
            assert type(layer['cx']) is list
            occupied = set()
            for edge in layer['cx']:
                assert type(edge) is list and len(edge) == 2
                assert all(type(site) is int and 0 <= site < qubits for site in edge)
                assert tuple(sorted(edge)) in native_edges
                assert not (set(edge) & occupied)
                occupied.update(edge)
                total_cx += 1
        assert total_cx <= family['max_cx']
        family_report = {'rounds': len(layers), 'cx_count': total_cx, 'directions': {}}
        reference_samples = baseline['measurements'](family, circuit)
        for inverse in (False, True):
            single_samples = []
            double_samples = []
            images = {}
            for site in range(qubits):
                for axis in 'XYZ':
                    initial = pauli(site, axis)
                    image = propagate(*initial, layers, inverse)
                    assert propagate(*image, layers, not inverse) == initial
                    images[site, axis] = image
                    single_samples.append((image[0] | image[1]).bit_count())
            for first, second in itertools.combinations(range(qubits), 2):
                for first_axis, second_axis in itertools.product('XYZ', repeat=2):
                    first_input = pauli(first, first_axis)
                    second_input = pauli(second, second_axis)
                    initial = (first_input[0] ^ second_input[0], first_input[1] ^ second_input[1])
                    image = propagate(*initial, layers, inverse)
                    first_image = images[first, first_axis]
                    second_image = images[second, second_axis]
                    assert image == (first_image[0] ^ second_image[0], first_image[1] ^ second_image[1])
                    assert propagate(*image, layers, not inverse) == initial
                    double_samples.append((image[0] | image[1]).bit_count())
            assert single_samples == reference_samples[2 * int(inverse)]
            assert double_samples == reference_samples[2 * int(inverse) + 1]
            direction_report = {}
            for kind, samples in [('single', single_samples), ('double', double_samples)]:
                metrics = summarize(samples, targets['min_' + kind],
                                    targets['mean_' + kind + '_milli'], qubits)
                direction_report[kind] = metrics
                assert metrics['passed'], (name, inverse, kind, metrics)
            family_report['directions']['inverse' if inverse else 'forward'] = direction_report
        report['families'][name] = family_report
    return report


if __name__ == '__main__':
    report = validate(ROOT / 'artifact.json')
    (ROOT / 'validation_report.json').write_text(json.dumps(report, indent=2) + '\n')
    for name, family in report['families'].items():
        print(f"{name}: {family['rounds']} rounds, {family['cx_count']} CNOTs")
        for direction, metrics in family['directions'].items():
            print(' ', direction, '; '.join(
                f"{kind} min={values['minimum']} mean={values['mean']:.9f}"
                for kind, values in metrics.items()))
    print('All native resource limits and all 24 target inequalities PASS.')
