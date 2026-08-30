import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def pair(score):
    return f"{score['core_score']:.4f} / {score['worst_family_score']:.4f}"


def main():
    statuses = {f'concept_{number}': read(f'concept_{number}/status.json')
                for number in [1, 2, 3]}
    final_names = {'solved', 'hard_open_candidate', 'hard_verified_achievable', 'invalid', 'rejected'}
    if any(status['status'] not in final_names for status in statuses.values()):
        raise RuntimeError('All concepts must have final empirical decisions before reporting.')
    retained = [name for name, status in statuses.items()
                if status['status'] in {'hard_open_candidate', 'hard_verified_achievable'}]
    if 'concept_3' not in retained:
        raise RuntimeError('The selected transport-falsification concept is not retained.')
    trials = []
    excluded = []
    for name in statuses:
        for path in sorted((ROOT / name / 'attempts').glob('*.run.json')):
            run = json.loads(path.read_text())
            attempt = path.name.removesuffix('.run.json')
            if 'finished_utc' not in run:
                raise RuntimeError(f'Attempt still running: {name}/{attempt}')
            trial = {
                'concept': name, 'attempt': attempt, 'generation': run['generation'],
                'model': run['model'], 'elapsed_seconds': run['elapsed_seconds'],
                'time_limit_seconds': run['time_limit_seconds'], 'timed_out': run['timed_out'],
                'participant_unchanged': run['participant_unchanged'],
                'evaluator_unchanged': run['evaluator_unchanged'],
                'score_path': f'{name}/attempts/{attempt}.score.json'
            }
            exclusion = ROOT / name / 'attempts' / f'{attempt}.infrastructure.json'
            if exclusion.exists():
                trial['exclusion_path'] = str(exclusion.relative_to(ROOT))
                excluded.append(trial)
            else:
                score = read(trial['score_path'])
                trial.update({key: score[key] for key in
                              ['core_score', 'worst_family_score', 'valid', 'passed']})
                if 'trace_ratio' in score:
                    trial['trace_ratio'] = score['trace_ratio']
                if name == 'concept_1' and attempt == statuses[name]['fresh_agent']['attempt']:
                    trial['nonofficial_quality_diagnostic'] = statuses[name].get('quality_diagnostic')
                trials.append(trial)
    primary = statuses['concept_3']
    report = {
        'paper': 'EPW: Electron-phonon coupling, transport and superconducting properties using maximally localized Wannier functions',
        'paper_arxiv_id': '1604.03525',
        'final_status': primary['status'], 'primary_retained_concept': 'concept_3',
        'retained_concepts': retained, 'solvability': primary['solvability'],
        'passing_solution_known': primary['passing_solution_known'],
        'built_concepts': 3, 'verification_modes': ['D', 'A', 'B'],
        'model': 'ultima-alpha', 'fresh_agent_time_limit_seconds': 3600,
        'total_task_generations': {name: status['generation'] for name, status in statuses.items()},
        'ratchet_generations': {name: status['ratchet_generations'] for name, status in statuses.items()},
        'concept_statuses': {name: status['status'] for name, status in statuses.items()},
        'fresh_trials': trials, 'excluded_infrastructure_trials': excluded,
        'evaluator_validation': {name: status['evaluator_validated'] for name, status in statuses.items()},
        'isolation_audit': 'authoring/isolation_audit.json',
        'package_audit': 'authoring/package_audit.json',
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'decision_scope': 'Empirical one-hour fresh ultima-alpha attempts, not a proof of universal hardness or infeasibility.'
    }
    (ROOT / 'status.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = [
        '# Hardness-discovery report', '',
        '## Concepts and verification modes', '',
        '| Concept | Primary mode | Final generation | Ratchet generations |',
        '|---|---|---:|---:|'
    ]
    descriptions = {
        'concept_1': ('Inverse Eliashberg spectral prediction', 'D — hidden prediction'),
        'concept_2': ('Temperature-transferable collision-event compression', 'A — baseline improvement'),
        'concept_3': ('Matched-observable transport falsification', 'B — counterexample/falsification')
    }
    for name, status in statuses.items():
        description, mode = descriptions[name]
        lines.append(f"| {name}: {description} | {mode} | {status['generation']} | {status['ratchet_generations']} |")
    lines += [
        '', '## Baseline and champion scores', '',
        'A/D entries are core / worst-family scores out of 100; their fixed target is 80 / 70.', '',
        '| Concept and generation | Runnable weak baseline | Champion from previous generation on this generation |',
        '|---|---:|---:|'
    ]
    for name in ['concept_1', 'concept_2']:
        original = read(f'{name}/evaluator/baseline_score.json')
        baseline = read(f'{name}/adversary/generation_2_baseline_score.json')
        previous = read(f'{name}/adversary/generation_2_champion_score.json')
        lines.append(f'| {name}, generation 1 | {pair(original)} | — |')
        lines.append(f'| {name}, generation 2 | {pair(baseline)} | {pair(previous)} |')
    baseline_witness = read('concept_3/evaluator/baseline_score.json')
    lines += [
        '', f"Concept 3 baseline trace ratio: **{baseline_witness['trace_ratio']:.9f}**, versus the fixed **1.75** witness target. No passing witness champion is known.",
        '', '## Fresh-agent scores', '',
        '| Concept / generation / attempt | Time (seconds) | Score | Target met |',
        '|---|---:|---:|---|'
    ]
    for trial in trials:
        scored = (f"trace ratio {trial['trace_ratio']:.9f}" if 'trace_ratio' in trial else pair(trial))
        lines.append(f"| {trial['concept']} / {trial['generation']} / {trial['attempt']} | {trial['elapsed_seconds']:.1f} | {scored} | {'yes' if trial['passed'] else 'no'} |")
    lines += [
        '', 'All scientific attempts use isolated fresh ultima-alpha sessions with a 3,600-second limit. One generation-1 spectral attempt terminated externally after 111.4 seconds and is excluded as infrastructure failure; its unchanged-task fresh retry is included.',
        '', 'The final spectral submission has official score 0 because CUDA-linked Torch cannot load under the 3-GiB address-space limit. This technical failure is not used alone as scientific hardness evidence. A separate, nonofficial run of the **unchanged submission**, with only the address-space ceiling raised to 16 GiB, completes in 31.2 seconds and scores **75.9348 / 73.7085**. Its mean physical loss is 23.37% above the core-target allowance, and it meets the predeclared substantial-failure margin (core at most 76). A conditional stratified-bootstrap 95% interval for core score is 75.1248–76.7166. This diagnostic is neither an official pass nor a repaired implementation. The frozen task wording did not distinguish RSS from address space; this resource ambiguity is explicitly not the sole basis for retention.',
        '', '## Counterexample search results', '',
        '- Spectral prediction: 6,144 private outcomes across four observation regimes identified the warm, noisy, weak-coupling failure. The original champion scored 75.6556 / 73.8040 there, and 75.5929 / 73.0059 on the new independent hidden generation. Public training and validation were regenerated in the same disclosed regime.',
        '- Collision compression: 28 private first-champion cases yielded 26 successes and two allocation failures. Larger published catalogues exposed the same memory-representation failure. The second fresh champion passed the task and all eight subsequent private probes, including up to 896 states and weakened inter-valley channels; the lowest probe score was 95.8668.',
        '- Matched-observable falsification: 30 privileged LP-vertex search restarts found a best admissible trace ratio of 1.653272048, not a passing witness. The fresh agent found 1.697351674; independent Fourier and shifted-grid collision solves agree to approximately 1.7e-14. No tested construction reaches 1.75.',
        '', '## Final status and solvability', ''
    ]
    for name, status in statuses.items():
        lines.append(f"- {name}: **{status['status']}**; solvability **{status['solvability']}**. {status['reason']}")
    lines += [
        '', f"Primary retained task: **concept_3**, **{primary['status']}**. Its target feasibility remains unknown. Exact-label and over-budget identity validation scores are not evidence of participant achievability.",
        '', '## Substantive capability failures', ''
    ]
    for name, status in statuses.items():
        lines.append(f"- {name}: {status['failure_capability']}")
    (ROOT / 'FINAL_REPORT.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({key: report[key] for key in
                      ['final_status', 'primary_retained_concept', 'retained_concepts', 'concept_statuses']}))


if __name__ == '__main__':
    main()
