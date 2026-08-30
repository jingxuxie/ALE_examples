import argparse
import hashlib
import itertools
import json
import math
import sys
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from certificate import integer_lower_bound
from graph import Graph, normalize
from optimize import feasible_edges, joint_lp_search, weighted_choices
from schedule import baseline_module
from solve import fingerprint, validate
from contract import canonical


def subsets(values):
    values = tuple(values)
    for mask in range(1 << len(values)):
        yield frozenset(value for position, value in enumerate(values) if mask >> position & 1)


def alternative_key(factors, boundary):
    best = None
    for ordering in itertools.permutations(range(len(factors))):
        assigned = {}
        encoded = []
        for position in ordering:
            name, axes = factors[position]
            converted = []
            for axis in axes:
                if axis not in assigned:
                    assigned[axis] = len(assigned)
                converted.append((axis not in boundary, assigned[axis]))
            encoded.append((name, tuple(converted)))
        encoded = (len(boundary), tuple(encoded))
        if best is None or encoded < best:
            best = encoded
    return best


def check_assumptions(case):
    if not all(type(value) is int and value > 0 for value in case['dimensions'].values()):
        raise ValueError('dimensions must be positive integers')
    for term in case['terms']:
        if not 3 <= len(term['inputs']) <= 6:
            raise ValueError('unexpected factor count')
        counts = Counter()
        for name, axes in term['inputs']:
            if len(axes) != len(set(axes)):
                raise ValueError('primitive input has a diagonal')
            if [case['index_types'][axis] for axis in axes] != case['tensors'][name]:
                raise ValueError('index and tensor space mismatch')
            counts.update(axes)
        if set(counts.values()) - {1, 2}:
            raise ValueError('unexpected index multiplicity')
        if len(term['output']) != len(set(term['output'])) or set(term['output']) != {axis for axis, count in counts.items() if count == 1}:
            raise ValueError('output does not equal degree-one boundary')


def relax_memory(case):
    volumes = [math.prod(case['dimensions'][case['index_types'][axis]] for axis in set(''.join(axes for name, axes in term['inputs']))) for term in case['terms']]
    relaxed = dict(case)
    relaxed['memory_cap'] = max(case['memory_cap'], 3 * max(volumes))
    return relaxed


def independent_enumeration(case, graph):
    reference_to_actual = {}
    actual_to_reference = {}
    expected_edges = set()
    raw_states = 0
    raw_edges = 0
    for term_number, term in enumerate(case['terms']):
        inputs = term['inputs']
        count = len(inputs)
        complete = (1 << count) - 1
        occurrence_masks = defaultdict(int)
        for position, (name, axes) in enumerate(inputs):
            for axis in axes:
                occurrence_masks[axis] |= 1 << position
        table = {}
        required = {}
        for mask in range(1, complete + 1):
            factors = [inputs[position] for position in range(count) if mask >> position & 1]
            present = {axis for axis, locations in occurrence_masks.items() if locations & mask}
            mandatory = frozenset(axis for axis in present if axis in term['output'] or occurrence_masks[axis] & (complete ^ mask))
            required[mask] = mandatory
            table[mask] = {}
            for optional in subsets(sorted(present - mandatory)):
                boundary = mandatory | optional
                key = alternative_key(factors, boundary)
                normalized, axes = normalize(factors, boundary)
                node_id = graph.lookup.get(normalized)
                if node_id is None:
                    raise ValueError('omitted subnetwork state')
                contract_key = canonical(tuple((name, tuple(indices)) for name, indices in factors), tuple(axes))
                if contract_key != graph.nodes[node_id].key[1]:
                    raise ValueError('state canonicalization disagrees with the validator')
                if key in reference_to_actual and reference_to_actual[key] != node_id:
                    raise ValueError('equivalent reference states were not merged')
                if node_id in actual_to_reference and actual_to_reference[node_id] != key:
                    raise ValueError('inequivalent reference states were merged')
                reference_to_actual[key] = node_id
                actual_to_reference[node_id] = key
                table[mask][boundary] = node_id
                raw_states += 1
        if graph.roots[term_number][0] != table[complete][frozenset(term['output'])] or graph.roots[term_number][2] != term['output']:
            raise ValueError('graph root demand does not match the requested output')
        for mask in range(1, complete + 1):
            if not mask & (mask - 1):
                continue
            anchor = mask & -mask
            left = (mask - 1) & mask
            while left:
                right = mask ^ left
                if left & anchor:
                    for (first_boundary, first), (second_boundary, second) in itertools.product(table[left].items(), table[right].items()):
                        union = first_boundary | second_boundary
                        if not required[mask] <= union:
                            raise ValueError('mandatory boundary vanished')
                        for optional in subsets(sorted(union - required[mask])):
                            boundary = required[mask] | optional
                            parent = table[mask][boundary]
                            cost = math.prod(case['dimensions'][case['index_types'][axis]] for axis in union)
                            if union - boundary:
                                cost *= 2
                            expected_edges.add((parent, min(first, second), max(first, second), cost))
                            raw_edges += 1
                left = (left - 1) & mask
    actual_edges = {(edge.parent, min(edge.children), max(edge.children), edge.cost) for edge in graph.edges}
    if set(actual_to_reference) != set(range(len(graph.nodes))) or expected_edges != actual_edges:
        raise ValueError('independent state/split enumeration disagrees with graph')
    allowed = feasible_edges(graph)
    if set(edge_id for choices in allowed.values() for edge_id in choices) != set(range(len(graph.edges))):
        raise ValueError('the supposedly unpruned graph still prunes operations')
    return {'independent_states_before_merging': raw_states, 'independent_operations_before_merging': raw_edges,
            'merged_nodes': len(graph.nodes), 'merged_edges': len(graph.edges),
            'two_canonicalizers_bijective': True, 'every_state_and_split_present': True,
            'memory_pruned_edges': 0,
            'same_child_edges': sum(edge.children[0] == edge.children[1] for edge in graph.edges)}


def alias_fixtures():
    cases = []
    scalar = {'dimensions': {'o': 3}, 'tensors': {'A': ['o'], 'B': ['o']},
              'index_types': {'i': 'o', 'j': 'o'}, 'memory_cap': 2,
              'terms': [{'inputs': [['A', 'i'], ['B', 'i'], ['A', 'j'], ['B', 'j']], 'output': ''}]}
    scalar_plan = {'steps': [{'id': 'shared', 'inputs': [['A', 'i'], ['B', 'i']], 'output': ''},
                             {'id': 'square', 'inputs': [['shared', ''], ['shared', '']], 'output': ''},
                             {'emit': 0, 'input': ['square', ''], 'output': ''}]}
    cases.append(('same_scalar_twice_independent_dummies', scalar, scalar_plan, True, 7, 2))
    matrix = {'dimensions': {'o': 2}, 'tensors': {'A': ['o', 'o'], 'B': ['o', 'o']},
              'index_types': {axis: 'o' for axis in 'ijklmn'}, 'memory_cap': 20,
              'terms': [{'inputs': [['A', 'ik'], ['B', 'kj'], ['A', 'ml'], ['B', 'ln']], 'output': 'ijmn'}]}
    matrix_plan = {'steps': [{'id': 'shared', 'inputs': [['A', 'ik'], ['B', 'kj']], 'output': 'ij'},
                             {'id': 'outer', 'inputs': [['shared', 'ij'], ['shared', 'mn']], 'output': 'ijmn'},
                             {'emit': 0, 'input': ['outer', 'ijmn'], 'output': 'ijmn'}]}
    cases.append(('same_matrix_twice_rebound_open_axes', matrix, matrix_plan, True, 32, 20))
    trace = dict(matrix, memory_cap=5, terms=[{'inputs': [['A', 'ik'], ['B', 'kj'], ['A', 'jl'], ['B', 'li']], 'output': ''}])
    trace_plan = {'steps': [{'id': 'shared', 'inputs': [['A', 'ik'], ['B', 'kj']], 'output': 'ij'},
                            {'id': 'trace', 'inputs': [['shared', 'ij'], ['shared', 'ji']], 'output': ''},
                            {'emit': 0, 'input': ['trace', ''], 'output': ''}]}
    cases.append(('same_matrix_twice_transposed_binding', trace, trace_plan, True, 24, 5))
    retained = {'dimensions': {'o': 2, 'v': 3}, 'tensors': {'A': ['o'], 'B': ['o'], 'C': ['v']},
                'index_types': {'i': 'o', 'a': 'v'}, 'memory_cap': 5,
                'terms': [{'inputs': [['A', 'i'], ['B', 'i'], ['C', 'a']], 'output': 'a'}]}
    retained_plan = {'steps': [{'id': 'hadamard', 'inputs': [['A', 'i'], ['B', 'i']], 'output': 'i'},
                               {'id': 'result', 'inputs': [['hadamard', 'i'], ['C', 'a']], 'output': 'a'},
                               {'emit': 0, 'input': ['result', 'a'], 'output': 'a'}]}
    cases.append(('retained_internal_index_summed_later', retained, retained_plan, True, 14, 5))
    premature_plan = {'steps': [{'id': 'wrong', 'inputs': [['A', 'i'], ['B', 'j']], 'output': ''},
                                {'id': 'result', 'inputs': [['wrong', ''], ['C', 'a']], 'output': 'a'},
                                {'emit': 0, 'input': ['result', 'a'], 'output': 'a'}]}
    cases.append(('premature_separate_sums_cannot_reconnect', retained, premature_plan, False, None, None))
    diagonal_plan = {'steps': [{'id': 'split', 'inputs': [['A', 'i'], ['B', 'j']], 'output': 'ij'},
                               {'id': 'result', 'inputs': [['split', 'ii'], ['C', 'a']], 'output': 'a'},
                               {'emit': 0, 'input': ['result', 'a'], 'output': 'a'}]}
    cases.append(('split_indices_cannot_be_diagonalized_later', dict(retained, memory_cap=100), diagonal_plan, False, None, None))
    reopened_plan = {'steps': [{'id': 'closed', 'inputs': [['A', 'i'], ['B', 'i']], 'output': ''},
                               {'id': 'result', 'inputs': [['closed', 'i'], ['C', 'a']], 'output': 'a'},
                               {'emit': 0, 'input': ['result', 'a'], 'output': 'a'}]}
    cases.append(('summed_dummy_cannot_be_rebound', retained, reopened_plan, False, None, None))
    output_storage = dict(scalar, terms=[{'inputs': [['A', 'i'], ['B', 'i']], 'output': ''}, scalar['terms'][0]])
    output_plan = {'steps': [{'id': 'shared', 'inputs': [['A', 'i'], ['B', 'i']], 'output': ''},
                             {'emit': 0, 'input': ['shared', ''], 'output': ''}, {'delete': 'shared'},
                             {'id': 'square', 'inputs': [['shared', ''], ['shared', '']], 'output': ''},
                             {'emit': 1, 'input': ['square', ''], 'output': ''}]}
    cases.append(('emitted_external_store_cannot_be_reused', output_storage, output_plan, False, None, None))
    records = []
    for name, case, plan, expected_valid, flops, peak in cases:
        try:
            result = validate(case, plan)
        except Exception as error:
            result = {'valid': False, 'reason': str(error)}
        if result['valid'] != expected_valid:
            raise ValueError('unexpected fixture result: ' + name)
        record = {'name': name, 'case': case, 'plan': plan, 'result': result, 'expected_valid': expected_valid}
        if expected_valid:
            if result['flops'] != flops or result['peak_elements'] != peak:
                raise ValueError('fixture arithmetic or allocation mismatch')
            graph = Graph(case, delayed=True)
            allowed = feasible_edges(graph)
            root = graph.roots[0][0]
            edge_ids = allowed[root]
            if name.startswith('same_') and not any(graph.edges[edge_id].children[0] == graph.edges[edge_id].children[1] for edge_id in edge_ids):
                raise ValueError('same-buffer binary operation was omitted')
            record['root_graph_edges'] = len(edge_ids)
            record['same_child_root_edges'] = sum(graph.edges[edge_id].children[0] == graph.edges[edge_id].children[1] for edge_id in edge_ids)
        records.append(record)
    return records


def run(output, verify_only=False):
    started = time.monotonic()
    directory = Path(__file__).resolve().parent
    concept = directory.parents[1]
    hidden = concept / 'evaluator/hidden'
    manifest = json.loads((hidden / 'manifest.json').read_text())
    sources = [concept / 'participant/workspace/contract.py', concept / 'participant/baseline/solve.py',
               concept / 'evaluator/evaluate.py', hidden / 'manifest.json', directory / 'graph.py',
               directory / 'certificate.py', directory / 'optimize.py', directory / 'schedule.py',
               directory / 'solve.py', directory / 'response_completeness.py']
    hashes = {str(path.relative_to(concept)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    if verify_only:
        saved = json.loads((output / 'summary.json').read_text())
        if saved['source_hashes'] != hashes:
            raise ValueError('validator, cases manifest, graph, or verifier changed since certification')
        saved_cases = {record['file']: record['original_case_sha256'] for record in saved['cases']}
    entries = [entry for entry in manifest['cases'] if entry['family'] == 'linear_response']
    if len(entries) != 6 or manifest['target_worst_family_speedup'] != 1.15:
        raise ValueError('unexpected frozen response family or target')
    output.mkdir(parents=True, exist_ok=True)
    fixtures = alias_fixtures()
    if not verify_only:
        (output / 'mechanism_fixtures.json').write_text(json.dumps(fixtures, indent=2) + '\n')
    records = []
    for entry in entries:
        case_started = time.monotonic()
        path = hidden / entry['file']
        case = json.loads(path.read_text())
        if verify_only and fingerprint(case) != saved_cases[entry['file']]:
            raise ValueError('frozen response input changed since certification')
        check_assumptions(case)
        baseline = validate(case, baseline_module().solve(case))
        if baseline['flops'] != entry['baseline']['flops']:
            raise ValueError('baseline changed')
        witness = validate(case, json.loads((directory / 'best' / (path.stem + '.plan.json')).read_text()))
        relaxed = relax_memory(case)
        graph = Graph(relaxed, delayed=True)
        enumeration = independent_enumeration(relaxed, graph)
        allowed = feasible_edges(graph)
        package_path = output / (path.stem + '.unbounded.bound.json')
        if verify_only:
            package = json.loads(package_path.read_text())
            if package['original_case_sha256'] != fingerprint(case) or package['relaxed_memory_cap'] != relaxed['memory_cap']:
                raise ValueError('certificate package input mismatch')
            certificate = package['certificate']
            optimization_seconds = None
        else:
            choices, bound = joint_lp_search(graph, allowed, weighted_choices(graph, allowed), seconds=30)
            certificate = bound['root_certificate']
            certificate['delayed_summation'] = True
            optimization_seconds = bound['seconds']
            package = {'original_case_sha256': fingerprint(case), 'original_memory_cap': case['memory_cap'],
                       'relaxed_memory_cap': relaxed['memory_cap'], 'certificate': certificate}
            package_path.write_text(json.dumps(package, indent=2) + '\n')
        lower = integer_lower_bound(graph, allowed, certificate)
        if lower <= 0 or lower > witness['flops']:
            raise ValueError('inconsistent certified lower bound')
        ratio = Fraction(baseline['flops'], lower)
        record = {'file': entry['file'], 'original_case_sha256': fingerprint(case), 'baseline_flops': baseline['flops'],
                  'best_valid_plan_flops': witness['flops'], 'universal_lower_flops': lower,
                  'universal_upper_speedup_fraction': [ratio.numerator, ratio.denominator],
                  'universal_upper_speedup': float(ratio), 'every_case_below_1_06_exact': 50 * baseline['flops'] < 53 * lower,
                  'unpruned_graph': enumeration, 'original_memory_cap': case['memory_cap'],
                  'relaxed_memory_cap': relaxed['memory_cap'], 'optimizer_seconds': optimization_seconds,
                  'elapsed_seconds': time.monotonic() - case_started}
        records.append(record)
        print(entry['file'], 'bound', lower, 'upper', float(ratio), 'unpruned_nodes', len(graph.nodes),
              'unpruned_edges', len(graph.edges), 'all_states_splits_checked', True, flush=True)
    product = math.prod(Fraction(record['baseline_flops'], record['universal_lower_flops']) for record in records)
    decimal_target = Fraction(23, 20)
    binary_target = Fraction.from_float(manifest['target_worst_family_speedup'])
    exact_margin = (decimal_target ** len(records)) / product
    if not product < binary_target ** len(records) or not all(record['every_case_below_1_06_exact'] for record in records):
        raise ValueError('response infeasibility is not certified')
    summary = {'classification': 'universal response-family infeasibility audit for the frozen declarative validator and cases',
               'date': '2026-08-28', 'verified_without_optimizer': verify_only,
               'scipy_imported': 'scipy' in sys.modules,
               'all_case_assumptions_verified': True, 'independent_unpruned_enumeration_verified': True,
               'all_integer_certificates_verified': True, 'all_mechanism_fixtures_verified': True,
               'response_family_impossible': True,
               'reason': 'Every valid useful plan embeds into the unpruned graph; the exact integer lower bounds put each response-case speedup below 1.06, hence below the 1.15 family gate.',
               'universal_family_upper_speedup': math.exp(sum(math.log(record['universal_upper_speedup']) for record in records) / len(records)),
               'universal_family_product_fraction': [product.numerator, product.denominator],
               'decimal_target_fraction': [23, 20], 'binary_target_fraction': [binary_target.numerator, binary_target.denominator],
               'target_power_divided_by_bound_product_fraction': [exact_margin.numerator, exact_margin.denominator],
               'exact_product_below_decimal_target_power': product < decimal_target ** len(records),
               'exact_product_below_actual_binary_target_power': product < binary_target ** len(records),
               'each_case_below_1_06_exact': True, 'source_hashes': hashes,
               'elapsed_seconds': time.monotonic() - started, 'cases': records}
    filename = 'verified_summary.json' if verify_only else 'summary.json'
    (output / filename).write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key not in {'cases', 'source_hashes'}}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'response_universal')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    run(args.output, args.verify_only)


if __name__ == '__main__':
    main()
