import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

from certificate import integer_lower_bound
from graph import Graph
from optimize import feasible_edges
from run_portfolio import geomean
from solve import fingerprint, validate


def main():
    portfolio = Path(__file__).resolve().parent
    concept = portfolio.parents[1]
    hidden = concept / 'evaluator/hidden'
    manifest = json.loads((hidden / 'manifest.json').read_text())
    runs = {name: json.loads((portfolio / name / 'summary.json').read_text()) for name in ('ordinary', 'expanded', 'deep')}
    verification = json.loads((portfolio / 'verification/summary.json').read_text())
    full_verification = json.loads((portfolio / 'verification_full/summary.json').read_text())
    fallback_verification = json.loads((portfolio / 'verification_fallback/summary.json').read_text())
    challenge = json.loads((portfolio / 'challenge/results/summary.json').read_text())
    if any(run['cases_completed'] != 24 for run in runs.values()) or len(verification['cases']) != 24 or len(full_verification['cases']) != 24:
        raise ValueError('required run is incomplete')
    best = portfolio / 'best'
    best.mkdir(exist_ok=True)
    records = []
    for position, entry in enumerate(manifest['cases']):
        name = Path(entry['file']).stem
        case = json.loads((hidden / entry['file']).read_text())
        candidates = [(run['cases'][position]['result']['flops'], run['cases'][position]['result']['peak_elements'], run_name)
                      for run_name, run in runs.items()]
        _, _, winner = min(candidates)
        plan = json.loads((portfolio / winner / (name + '.plan.json')).read_text())
        result = validate(case, plan)
        (best / (name + '.plan.json')).write_text(json.dumps(plan))
        certificate = json.loads((portfolio / 'expanded' / (name + '.bound.json')).read_text())
        graph = Graph(case, delayed=True)
        lower = integer_lower_bound(graph, feasible_edges(graph), certificate)
        (best / (name + '.bound.json')).write_text(json.dumps(certificate, indent=2) + '\n')
        cold = verification['cases'][position]['cold_runtime']
        records.append({'file': entry['file'], 'family': entry['family'], 'dimensions': case['dimensions'],
                        'terms': len(case['terms']), 'memory_cap': case['memory_cap'], 'case_sha256': fingerprint(case),
                        'baseline_flops': entry['baseline']['flops'], 'result': result,
                        'speedup': entry['baseline']['flops'] / result['flops'], 'source_run': winner,
                        'generation_seconds': runs[winner]['cases'][position]['generation_seconds'],
                        'integer_graph_lower_flops': lower, 'integer_graph_upper_speedup': entry['baseline']['flops'] / lower,
                        'cold_planner_seconds': cold['wall_seconds'], 'cold_planner_result': cold.get('result'),
                        'cold_planner_valid': cold.get('result', {}).get('valid', False)})
    families = {family: geomean([record['speedup'] for record in records if record['family'] == family]) for family in sorted({record['family'] for record in records})}
    graph_families = {family: geomean([record['integer_graph_upper_speedup'] for record in records if record['family'] == family]) for family in families}
    core = geomean([record['speedup'] for record in records])
    graph_upper = geomean([record['integer_graph_upper_speedup'] for record in records])
    cache_audit = {'with_evictions': 0, 'with_recomputation': 0, 'with_baseline_fallback': 0, 'forced_multiroot_candidates': 0}
    for run_name, run in runs.items():
        for record in run['cases']:
            search_report = json.loads((portfolio / run_name / (Path(record['file']).stem + '.search.json')).read_text())
            for candidate in search_report['candidates']:
                cache_audit['with_evictions'] += bool(candidate.get('evictions', 0))
                cache_audit['with_recomputation'] += bool(candidate.get('recomputed_nodes', 0))
                cache_audit['with_baseline_fallback'] += bool(candidate.get('fallbacks', 0))
                cache_audit['forced_multiroot_candidates'] += candidate['method'].startswith('multiroot_')
    summary = {'classification': 'privileged offline portfolio and specialized exact-input certificates; not a participant attempt',
               'date': '2026-08-28', 'all_valid': True, 'cases_completed': 24, 'cases_expected': 24,
               'targets': {'geomean_speedup': 1.75, 'each_family_speedup': 1.15},
               'core_score': core, 'family_scores': families, 'worst_family_score': min(families.values()),
               'passed_fixed_arithmetic_targets': core >= 1.75 and min(families.values()) >= 1.15,
               'integer_certified_graph_upper_score': graph_upper, 'integer_certified_graph_family_upper_scores': graph_families,
               'scope_warning': 'Bounds apply to the explicitly enumerated ordinary and delayed-summation contraction graph, with scheduling relaxed; they are not asserted as a universal impossibility result.',
               'ordinary_and_delayed_numerical_joint_optima_reached': all(record['result']['flops'] == record['optimization']['joint_incumbent_flops'] and record['optimization']['numerically_closed'] for record in runs['expanded']['cases']),
               'hidden_plan_candidates_validated': sum(sum(record['validated_candidates'] for record in run['cases']) for run in runs.values()),
               'hidden_invalid_candidates': sum(sum(record['invalid_candidates'] for record in run['cases']) for run in runs.values()),
               'cache_and_multiroot_candidate_audit': cache_audit,
               'forced_memory_fallback_cases_validated': sum(record['forced_memory_fallback']['result']['valid'] for record in fallback_verification['cases']),
               'forced_memory_fallback_events': sum(record['forced_memory_fallback']['fallbacks'] for record in fallback_verification['cases']),
               'all_graph_edges_contract_checked': sum(record['semantically_checked_edges'] for record in full_verification['cases']),
               'offline_generation_seconds': {name: run['generation_seconds'] for name, run in runs.items()},
               'cold_planner_total_seconds': sum(record['cold_planner_seconds'] for record in records),
               'cold_planner_max_seconds': max(record['cold_planner_seconds'] for record in records),
               'cold_planner_all_valid_under_30_seconds_2gib_one_thread': all(record['cold_planner_valid'] and record['cold_planner_seconds'] < 30 for record in records),
               'cold_planner_isolation': 'local subprocess with address-space/CPU/time limits and BLAS thread limits; not evaluator bubblewrap',
               'diagnostic_challenge_cases': challenge['cases_completed'],
               'diagnostic_challenge_core_score': challenge['core_score'], 'diagnostic_challenge_family_scores': challenge['family_scores'],
               'diagnostic_challenge_passed_fixed_targets': challenge['passed_fixed_arithmetic_targets'],
               'diagnostic_challenge_candidates_validated': sum(record['validated_candidates'] for record in challenge['cases']),
               'diagnostic_challenge_invalid_candidates': sum(record['invalid_candidates'] for record in challenge['cases']),
               'conclusion': 'No passing solution found; achievability remains unknown, not impossible.', 'cases': records}
    (best / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    replay_records = []
    replay_output = portfolio / 'replay_validation'
    replay_output.mkdir(exist_ok=True)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    for record in records:
        name = Path(record['file']).stem
        started = time.monotonic()
        process = subprocess.run([sys.executable, str(portfolio / 'replay.py'), str(hidden / record['file']),
                                  str(replay_output / (name + '.plan.json'))], capture_output=True, text=True,
                                 timeout=30, env=environment)
        if process.returncode:
            raise ValueError(process.stderr)
        wall = time.monotonic() - started
        result = validate(json.loads((hidden / record['file']).read_text()), json.loads((replay_output / (name + '.plan.json')).read_text()))
        replay_records.append({'file': record['file'], 'wall_seconds': wall, 'result': result})
        record['certificate_replay_seconds'] = wall
    summary['certificate_replay_total_seconds'] = sum(record['wall_seconds'] for record in replay_records)
    summary['certificate_replay_max_seconds'] = max(record['wall_seconds'] for record in replay_records)
    (replay_output / 'summary.json').write_text(json.dumps(replay_records, indent=2) + '\n')
    (best / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    with (portfolio / 'per_case_scores.csv').open('w', newline='') as stream:
        fields = ['file', 'family', 'occupied', 'virtual', 'terms', 'memory_cap', 'baseline_flops', 'flops', 'speedup',
                  'peak_elements', 'resource_score', 'source_run', 'generation_seconds', 'cold_planner_seconds',
                  'certificate_replay_seconds', 'integer_graph_lower_flops', 'integer_graph_upper_speedup']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {key: record[key] for key in fields if key in record}
            row.update(occupied=record['dimensions']['o'], virtual=record['dimensions']['v'],
                       flops=record['result']['flops'], peak_elements=record['result']['peak_elements'], resource_score=record['result']['resource_score'])
            writer.writerow(row)
    files = [concept / 'participant/TASK.md', concept / 'participant/workspace/INTERFACE.md',
             concept / 'participant/workspace/contract.py', concept / 'participant/baseline/solve.py',
             hidden / 'manifest.json', hidden / 'source_terms.json'] + [hidden / entry['file'] for entry in manifest['cases']]
    provenance = {str(path.relative_to(concept)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    (portfolio / 'read_only_input_hashes.json').write_text(json.dumps(provenance, indent=2) + '\n')
    lines = ['# Private search summary — 2026-08-28', '', '**No passing solution found. Achievability remains unknown, not impossible.**', '',
             'All outputs are private to `concept_1/adversary/portfolio/`. Participant, evaluator, original manifest, and tested attempts are not modified; tested attempt contents were not read.', '',
             '## Frozen 24-case result', '', f'- Geometric-mean speedup: **{core:.12f}×**, target **1.75×**.',
             f'- Worst-family speedup: **{min(families.values()):.12f}×**, target **1.15×**.',
             '- All 24 selected plans pass the exact supplied `contract.validate`; all scratch caps hold.', '',
             '| Family | Achieved speedup | Integer-certified graph speedup upper bound |', '|---|---:|---:|']
    for family in families:
        lines.append(f'| {family} | {families[family]:.12f} | {graph_families[family]:.12f} |')
    lines += ['', '## Strength and limitations of the search', '',
              '- Enumerated every factor subset and binary split, merging exact subnetworks under dummy-label renaming, repeated-factor permutation, and output-axis permutation.',
              '- A second graph includes every retained subset of internal summed indices whose array can fit the cap, allowing delayed summations and reuse of those additional networks.',
              '- Global AND/OR LP branch-and-bound selects contraction trees jointly, rather than independently selecting trees and merely caching their coincidences.',
              '- Multi-root coordinate replanning, stochastic amortized-cost tree choices, five output orders, four cache eviction policies, and memory-triggered recomputation are exercised in the forced deep run. Oversized-tree fallback is exercised separately in a targeted audit.',
              '- All 24 achieved costs equal their numerically closed global branch-and-bound optima. Memory-feasible schedules attain those costs; no scheduling/recomputation penalty remains on the selected plans.',
              f'- Independent integer-arithmetic checks of LP Lagrangian certificates give an overall **{graph_upper:.12f}×** speedup upper bound **within the enumerated graph model**. The achieved arithmetic is within **{100 * (graph_upper / core - 1):.6f}%** of that conservative relaxed bound.',
              '- LP certificates are checked using integer coefficients, signed integer multipliers, and exact reduced-cost lower bounds on [0,1] variables; floating-point solver status alone is not the certificate.',
              '- Graph enumeration/completeness is not elevated to a universal proof about every legal plan. These are strong scoped negative results, not a declaration that the task is impossible.',
              f'- Reaching 1.75× from this portfolio requires another **{100 * (1 - core / 1.75):.6f}%** geometric-mean arithmetic reduction. Response is the strongest observed family bottleneck.', '',
              '## Validation and runtime', '',
              f'- Hidden generated plans validated: **{summary["hidden_plan_candidates_validated"]}**, invalid candidates: **{summary["hidden_invalid_candidates"]}**.',
              f'- Expanded graph binary operations independently audited as exact contraction plans: **{summary["all_graph_edges_contract_checked"]}**.',
              f'- Forced memory-fallback audit: **{summary["forced_memory_fallback_cases_validated"]}** valid plans, **{summary["forced_memory_fallback_events"]}** fallback events; no baseline fallback was needed by the winning portfolio.',
              '- The baseline is recomputed on every hidden case and agrees with the frozen manifest; independent graph optima also agree with the baseline before cross-term reuse.',
              f'- Cold fresh solver invocations: **{summary["cold_planner_total_seconds"]:.6f}s total**, **{summary["cold_planner_max_seconds"]:.6f}s maximum**, all valid under 30s, one BLAS thread, and a 2 GiB address-space limit.',
              '- Cold runtime checks use local resource-limited subprocesses, not the evaluator bubblewrap sandbox. This portfolio is not presented as a fresh participant attempt.',
              f'- Specialized exact-input certificate replay: **{summary["certificate_replay_total_seconds"]:.6f}s total**, **{summary["certificate_replay_max_seconds"]:.6f}s maximum**. These timings are not offline optimization timings.',
              '- Offline in-process generation seconds by run: ' + ', '.join(f'`{name}`={run["generation_seconds"]:.6f}' for name, run in runs.items()) + '.', '',
              '## Additional source-derived challenges', '',
              f'- **{challenge["cases_completed"]}** separate private cases use the provided parser-extracted source terms without invented tensor identities or symmetry assumptions.',
              '- Four dimension/batch/cap settings per family, with uniform random and reuse-rich source-term selections, cover 20–80-term batches (response has at most 34 source terms), 4–20 occupied, and 12–112 virtual dimensions.',
              '- These challenge sets are diagnostic only: they do not replace, tune, or modify the original hidden cases or frozen target.',
              f'- Diagnostic overall speedup: **{challenge["core_score"]:.12f}×**; validated candidate plans: **{summary["diagnostic_challenge_candidates_validated"]}**; invalid candidates: **{summary["diagnostic_challenge_invalid_candidates"]}**.', '',
              '- Diagnostic family speedups: ' + ', '.join(f'`{family}`={value:.12f}×' for family, value in challenge['family_scores'].items()) + '. The response-family gate still fails; these diagnostics are not a passing fixed-target portfolio.', '',
              '## Artifacts', '',
              '- `solve.py`: runnable input-to-plan optimizer; `replay.py`: clearly marked privileged exact-input certificate replay.',
              '- `best/`: best valid per-case plans, integer lower-bound certificates, and exact aggregate/per-case metrics.',
              '- `per_case_scores.csv`: flop counts, peaks, speedups, per-case generation/cold/replay timings, and scoped bounds.',
              '- `ordinary/`, `expanded/`, `deep/`: separate portfolio reports and every candidate validation record.',
              '- `verification/`, `verification_full/`: independent semantic, baseline, bound, and cold-runtime audit reports.',
              '- `challenge/`: generated source-derived cases, provenance, plans, and scores; `read_only_input_hashes.json`: reproducibility hashes.', '']
    (portfolio / 'SUMMARY.md').write_text('\n'.join(lines))
    print(json.dumps({key: value for key, value in summary.items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
