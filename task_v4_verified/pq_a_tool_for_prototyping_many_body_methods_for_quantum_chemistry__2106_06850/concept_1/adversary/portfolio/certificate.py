import hashlib
import json


def case_digest(case):
    return hashlib.sha256(json.dumps(case, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def integer_lower_bound(graph, allowed, certificate):
    if case_digest(graph.case) != certificate['case_sha256']:
        raise ValueError('certificate is for a different case')
    cutoff = certificate['edge_cost_cutoff']
    roots = {root[0] for root in graph.roots}
    edge_ids = [edge_id for node_id in graph.topological for edge_id in allowed.get(node_id, []) if graph.edges[edge_id].cost <= cutoff]
    if edge_ids != certificate['edge_ids']:
        raise ValueError('graph edge set does not match certificate')
    reduced = {edge_id: graph.edges[edge_id].cost for edge_id in edge_ids}
    outgoing = {node_id: [edge_id for edge_id in allowed.get(node_id, []) if edge_id in reduced] for node_id in range(len(graph.nodes))}
    constant = 0
    for node_id, multiplier in certificate['node_duals']:
        if type(multiplier) is not int or multiplier > 0 or node_id in roots or graph.nodes[node_id].tensor:
            raise ValueError('invalid node multiplier')
        constant += multiplier
        for edge_id in outgoing[node_id]:
            reduced[edge_id] -= multiplier
    for node_id, multiplier in certificate['root_duals']:
        if type(multiplier) is not int or node_id not in roots:
            raise ValueError('invalid root multiplier')
        constant += multiplier
        for edge_id in outgoing[node_id]:
            reduced[edge_id] -= multiplier
    for edge_id, child, multiplier in certificate['dependency_duals']:
        if type(multiplier) is not int or multiplier > 0 or edge_id not in reduced:
            raise ValueError('invalid dependency multiplier')
        if child not in graph.edges[edge_id].children or graph.nodes[child].tensor:
            raise ValueError('invalid child dependency')
        reduced[edge_id] -= multiplier
        for child_edge in outgoing[child]:
            reduced[child_edge] += multiplier
    bound = min(cutoff, constant + sum(min(0, value) for value in reduced.values()))
    if bound != certificate['integer_lower_flops']:
        raise ValueError('incorrect claimed integer bound')
    return bound


def from_duals(graph, edge_ids, cutoff, inequalities, equalities, result, scale):
    certificate = {'case_sha256': case_digest(graph.case), 'edge_cost_cutoff': cutoff,
                   'edge_ids': edge_ids, 'node_duals': [], 'root_duals': [], 'dependency_duals': [],
                   'scope': 'integer-arithmetic Lagrangian certificate for the enumerated global binary-contraction graph; local memory allocations only; no claim of universal completeness'}
    reduced = {edge_id: graph.edges[edge_id].cost for edge_id in edge_ids}
    outgoing = {node_id: [edge_id for edge_id in graph.nodes[node_id].edges if edge_id in reduced] for node_id in range(len(graph.nodes))}
    constant = 0
    for description, marginal in zip(inequalities, result.ineqlin.marginals):
        multiplier = min(0, round(float(marginal) * scale))
        if multiplier == 0:
            continue
        if description[0] == 'node':
            node_id = description[1]
            certificate['node_duals'].append([node_id, multiplier])
            constant += multiplier
            for edge_id in outgoing[node_id]:
                reduced[edge_id] -= multiplier
        else:
            edge_id, child = description[1:]
            certificate['dependency_duals'].append([edge_id, child, multiplier])
            reduced[edge_id] -= multiplier
            for child_edge in outgoing[child]:
                reduced[child_edge] += multiplier
    for node_id, marginal in zip(equalities, result.eqlin.marginals):
        multiplier = round(float(marginal) * scale)
        if multiplier == 0:
            continue
        certificate['root_duals'].append([node_id, multiplier])
        constant += multiplier
        for edge_id in outgoing[node_id]:
            reduced[edge_id] -= multiplier
    certificate['integer_lower_flops'] = min(cutoff, constant + sum(min(0, value) for value in reduced.values()))
    return certificate


def main():
    import argparse
    from pathlib import Path
    from graph import Graph
    from optimize import feasible_edges
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=Path)
    parser.add_argument('certificate', type=Path)
    args = parser.parse_args()
    case = json.loads(args.case.read_text())
    certificate = json.loads(args.certificate.read_text())
    graph = Graph(case, delayed=certificate.get('delayed_summation', False))
    bound = integer_lower_bound(graph, feasible_edges(graph), certificate)
    print(json.dumps({'verified': True, 'integer_lower_flops': bound}))


if __name__ == '__main__':
    main()
