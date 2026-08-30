import collections
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ['PARTICIPANT']) / 'workspace'))
from model import baseline_order, improvement, metrics


def objective(record):
    return 0.7 * math.log(record['peak']) + 0.3 * math.log(record['qubit_time'])


def independently_measure(case, order):
    count = len(case['nodes'])
    assert len(order) == count
    assert all(type(node) is int for node in order)
    assert set(order) == set(range(count))
    edges = case['edges']
    incoming = [[] for _ in range(count)]
    outgoing = [[] for _ in range(count)]
    for edge_index, (source, destination, width) in enumerate(edges):
        incoming[destination].append(edge_index)
        outgoing[source].append(edge_index)
    live_edges = set()
    peak = 0
    area = 0
    for node in order:
        assert set(incoming[node]) <= live_edges
        live_edges.difference_update(incoming[node])
        input_width = sum(edges[edge][2] for edge in incoming[node])
        output_width = sum(edges[edge][2] for edge in outgoing[node])
        footprint = sum(edges[edge][2] for edge in live_edges) + max(input_width, output_width) + case['nodes'][node]['workspace']
        area += footprint * case['nodes'][node]['duration']
        live_edges.update(outgoing[node])
        peak = max(peak, footprint, sum(edges[edge][2] for edge in live_edges))
    assert not live_edges
    return {'peak': peak, 'qubit_time': area}


cases = json.loads(Path(os.environ['INPUT']).read_text())['cases']
schedules = json.loads(Path('schedules.json').read_text())['schedules']
assert set(schedules) == {case['id'] for case in cases}
families = collections.defaultdict(list)
records = []
for case in cases:
    before = metrics(case, baseline_order(case))
    order = schedules[case['id']]
    after = metrics(case, order)
    for directory in sys.argv[1:] or ['results']:
        path = Path(directory) / (case['id'] + '.txt')
        if path.exists():
            candidate = list(map(int, path.read_text().split()))
            result = metrics(case, candidate)
            if 20 * result['peak'] <= 21 * before['peak'] and objective(result) < objective(after):
                after = result
                order = candidate
    assert 20 * after['peak'] <= 21 * before['peak']
    assert independently_measure(case, order) == after
    schedules[case['id']] = order
    ratio = improvement(before, after)
    families[case['family']].append(math.log(ratio))
    record = {'id': case['id'], 'family': case['family'], 'baseline': before, 'submitted': after, 'ratio': ratio}
    records.append(record)
    print(case['id'], after, round(ratio, 5))
family_scores = {family: math.exp(sum(values) / len(values)) for family, values in families.items()}
core = math.exp(sum(math.log(record['ratio']) for record in records) / len(records))
report = {'core_score': core, 'family_scores': family_scores, 'worst_family_score': min(family_scores.values()), 'peak_guard': True, 'cases': records}
report['passed'] = core >= 1.70 and report['worst_family_score'] >= 1.18
Path('schedules.json').write_text(json.dumps({'schedules': schedules}, separators=(',', ':')) + '\n')
Path('metrics.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'cases'}, indent=2))
