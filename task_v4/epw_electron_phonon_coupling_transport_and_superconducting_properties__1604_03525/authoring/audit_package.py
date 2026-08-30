import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL_STATUSES = {
    'solved', 'hard_open_candidate', 'hard_verified_achievable', 'invalid', 'rejected'
}


def digest_tree(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob('*'))
        if path.is_file() and '__pycache__' not in path.parts
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-pending', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'authoring/package_audit.json')
    args = parser.parse_args()
    failures = []
    checks = []

    def check(condition, description):
        checks.append({'check': description, 'passed': bool(condition)})
        if not condition:
            failures.append(description)

    concepts = sorted(ROOT.glob('concept_[0-9]'))
    check(len(concepts) == 3, 'exactly three built concepts')
    modes = set()
    genuine_trials = 0
    excluded_trials = 0
    pending_trials = 0
    for concept in concepts:
        name = concept.name
        status = json.loads((concept / 'status.json').read_text())
        modes.add(status['verification_mode'].split('_')[0])
        for relative in [
            'participant/TASK.md', 'participant/input', 'participant/workspace',
            'participant/baseline', 'evaluator/evaluate.py', 'evaluator/hidden',
            'attempts', 'champions', 'adversary', 'status.json'
        ]:
            check((concept / relative).exists(), f'{name}: required {relative}')
        check(not any(path.is_symlink() for path in (concept / 'participant').rglob('*')),
              f'{name}: participant has no symlinks')
        validation = json.loads((concept / 'adversary/evaluator_validation.json').read_text())
        check(validation.get('valid') is True, f'{name}: independent evaluator validation')
        check(status.get('evaluator_validated') is True and status.get('isolation_validated') is True,
              f'{name}: validated status flags')
        check(status['generation'] <= 3 and status['ratchet_generations'] <= 3,
              f'{name}: generation limits respected')
        is_final = status['status'] in FINAL_STATUSES
        check(is_final or args.allow_pending, f'{name}: final empirical decision')
        runs = sorted((concept / 'attempts').glob('*.run.json'))
        check(bool(runs), f'{name}: fresh-agent attempt exists')
        for path in runs:
            run = json.loads(path.read_text())
            trial = path.name.removesuffix('.run.json')
            label = f'{name}/{trial}'
            check(run['model'] == 'ultima-alpha', f'{label}: required model')
            check(run['time_limit_seconds'] == 3600 and run['initial_output_empty'],
                  f'{label}: one-hour fresh output contract')
            command = run['command']
            check(Path(command[0]).name == 'run_allowlisted_codex.sh'
                  and '--task-read-only' in command, f'{label}: required allowlist runner')
            exclusion = concept / 'attempts' / f'{trial}.infrastructure.json'
            if exclusion.exists():
                excluded_trials += 1
                check(run.get('returncode') == -15 and not run.get('timed_out'),
                      f'{label}: excluded infrastructure termination, not a task failure')
                continue
            generation = run['generation']
            archive = concept / 'champions' / f'generation_{generation}'
            frozen = archive if (archive / 'participant').is_dir() else concept
            for section in ['participant', 'evaluator']:
                check(digest_tree(frozen / section) == run[f'{section}_before'],
                      f'{label}: preserved frozen {section}')
            if 'finished_utc' not in run:
                pending_trials += 1
                check(args.allow_pending, f'{label}: attempt finished')
                continue
            genuine_trials += 1
            check(run['participant_unchanged'] and run['evaluator_unchanged'],
                  f'{label}: no task mutation during trial')
            check(run['elapsed_seconds'] <= 3618,
                  f'{label}: deadline and bounded cleanup respected')
            score_path = concept / 'attempts' / f'{trial}.score.json'
            check(score_path.is_file(), f'{label}: authoritative score exists')
            if score_path.is_file():
                score = json.loads(score_path.read_text())
                required = ['core_score', 'worst_family_score', 'runtime_resource_score',
                            'valid', 'passed', 'reason']
                check(all(key in score for key in required), f'{label}: required score fields')
        if is_final:
            check(status.get('final_status') == status['status'], f'{name}: final status agrees')
            if status['status'] == 'solved':
                check(status['passing_solution_known'] and status['solvability'] == 'demonstrated',
                      f'{name}: solved status has a known passing solution')
            if status['status'] == 'hard_open_candidate':
                check(not status['passing_solution_known'] and status['solvability'] == 'unknown',
                      f'{name}: open status does not claim achievability')
            if status.get('fresh_agent'):
                score = json.loads((concept / 'attempts' /
                                    (status['fresh_agent']['attempt'] + '.score.json')).read_text())
                check(score['passed'] == (status['status'] == 'solved'),
                      f'{name}: final status agrees with scored fresh submission')
                if status['status'] == 'hard_open_candidate' and 'hardness_margin' in status:
                    margin = status['hardness_margin']
                    quality = score
                    if not score['valid']:
                        quality = status.get('quality_diagnostic', {})
                        check(quality.get('valid') is True and quality.get('submission_unchanged') is True,
                              f'{name}: scientific hardness is not inferred solely from execution failure')
                        if quality.get('score_artifact'):
                            diagnostic = json.loads((concept / quality['score_artifact']).read_text())
                            check(diagnostic['core_score'] == quality['core_score']
                                  and diagnostic['diagnostic_only'] and not diagnostic['passed'],
                                  f'{name}: nonofficial diagnostic accurately represented')
                    check(quality.get('core_score', 100) <= margin['maximum_core_for_substantial_failure']
                          or quality.get('worst_family_score', 100) <= margin['maximum_worst_family_for_substantial_failure'],
                          f'{name}: predeclared substantial-failure margin met')
    check(len(modes) >= 3, 'at least three distinct verification modes')
    isolation = json.loads((ROOT / 'authoring/isolation_audit.json').read_text())
    check(isolation.get('valid') is True, 'filesystem and network isolation probes passed')
    report = {
        'valid': not failures, 'final': not args.allow_pending and not pending_trials,
        'concept_count': len(concepts), 'verification_modes': sorted(modes),
        'genuine_completed_trials': genuine_trials, 'excluded_infrastructure_trials': excluded_trials,
        'pending_trials': pending_trials, 'failures': failures, 'checks': checks
    }
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'checks'}))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
