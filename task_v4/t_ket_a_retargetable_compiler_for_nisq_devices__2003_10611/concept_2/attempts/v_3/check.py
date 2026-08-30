import argparse
import json
import sys
import time
from pathlib import Path

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_2/adversary/generation_3/participant/input')
sys.path.insert(0, str(ASSETS))
from benchmark import evaluate_witness
from router import hardware, relabelings, route, settings, transform
from validation import load_witness, validate

parser = argparse.ArgumentParser()
parser.add_argument('witness', type=Path)
parser.add_argument('--full', action='store_true')
arguments = parser.parse_args()
witness = load_witness(arguments.witness)
count, edges, gates, costs = validate(witness)
stem = arguments.witness.with_suffix('')
with open(str(stem) + '.ops', 'w') as output:
    for operation in witness['route']:
        endpoints = operation[1:] if operation[0] == 'swap' else operation[2:]
        print(int(operation[0] == 'swap'), edges.index(tuple(sorted(endpoints))), file=output)
started = time.monotonic()
if arguments.full:
    result = evaluate_witness(witness)
    Path(str(stem) + '_checked.json').write_text(json.dumps(witness, indent=2) + '\n')
    Path(str(stem) + '_result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(arguments.witness.name, {key: result[key] for key in ('valid', 'passed', 'reference', 'gate_count', 'resource_score')}, flush=True)
    print([(family['name'], family['portfolio_swaps'], family['best_setting']) for family in result['families']], flush=True)
else:
    all_costs = []
    policies = [setting for setting in settings() if setting['horizon']]
    families = [family for family in relabelings(count) if family[0] != 'logical-47']
    for family_index, (name, logical, physical) in enumerate(families):
        mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
        results = []
        for policy_index, policy in enumerate(policies):
            measured = route(mapped_gates, count, mapped_edges, initial, policy)
            results.append(measured['swaps'])
            all_costs.append((measured['swaps'], family_index * len(policies) + policy_index))
        print(name, min(results), policies[results.index(min(results))]['name'], flush=True)
    Path(str(stem) + '_python_costs.json').write_text(json.dumps(all_costs) + '\n')
    ordered = sorted(all_costs)
    Path(str(stem) + '.tests').write_text('\n'.join(str(identifier) for _, identifier in ordered[:30]) + '\n')
    print('reference', costs, 'gates', len(gates), 'minimum', ordered[0], flush=True)
print('elapsed', time.monotonic() - started, flush=True)
