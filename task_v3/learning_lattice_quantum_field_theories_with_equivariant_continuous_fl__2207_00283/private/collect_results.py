import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def summarize(report):
    if report is None:
        return None
    family = report.get('family_scores')
    if family is None:
        family = {name: entry['score'] for name, entry in report.get('families', report.get('groups', {})).items()}
    score = report.get('mean_core', report.get('score'))
    cases = report.get('cases', [])
    times = [row.get('wall_seconds', row.get('seconds', row.get('execution', {}).get('seconds'))) for row in cases]
    times = [value for value in times if value is not None]
    return {'mean_core': score, 'worst_family': min(family.values()) if family else report.get('worst_family'),
            'families': family, 'case_count': len(cases) if 'cases' in report else None,
            'maximum_case_seconds': max(times) if times else report.get('elapsed_seconds'),
            'failures': report.get('failures'), 'normalized_skill': report.get('normalized_skill_mean', report.get('weak_strong_normalized_score'))}


def main():
    scalar = ROOT / 'pilots/04_scalar_checkpoint'
    anchors = {}
    for pool in ('test', 'challenge'):
        weak = load(scalar / f'attempt/identity-{pool}.json')
        strong = load(scalar / f'attempt/strong-isolated-{pool}.json')
        if weak and strong:
            anchors[pool] = {'weak_score': weak['score'], 'strong_score': strong['score'],
                             'weak_source': f'attempt/identity-{pool}.json',
                             'strong_source': f'attempt/strong-isolated-{pool}.json'}
    (scalar / 'private/reference/empirical_anchors.json').write_text(json.dumps(anchors, indent=2))
    records = []
    for pilot in sorted((ROOT / 'pilots').iterdir()):
        if not pilot.is_dir():
            continue
        private = pilot / 'private'
        launch = load(private / 'initial_launch.json')
        exit_info = load(private / 'initial_exit.json')
        duration = None
        if launch and exit_info:
            duration = (datetime.fromisoformat(exit_info['finished'].replace('Z', '+00:00'))
                        - datetime.fromisoformat(launch['started'].replace('Z', '+00:00'))).total_seconds()
        record = {'concept': pilot.name, 'model': launch.get('model') if launch else None,
                  'attempt_seconds': duration, 'exit': exit_info,
                  'initial': summarize(load(private / 'initial_report.json')),
                  'challenge': summarize(load(private / 'challenge_report.json')),
                  'stress': summarize(load(private / 'stress_report.json'))}
        if pilot.name == '04_scalar_checkpoint':
            record['refined_oracle_diagnostic'] = {
                pool: summarize(load(private / f'refined_{pool}_report.json'))
                for pool in ('test', 'challenge')
            }
            for stage, pool in (('initial', 'test'), ('challenge', 'challenge')):
                if record[stage] is not None and pool in anchors:
                    calibration = anchors[pool]
                    record[stage]['normalized_skill'] = (record[stage]['mean_core'] - calibration['weak_score']) / (calibration['strong_score'] - calibration['weak_score'])
        records.append(record)
    selection = load(ROOT / 'selection.json')
    status = selection['status'] if selection else 'screening'
    (ROOT / 'private/tournament.json').write_text(json.dumps({'status': status, 'concepts': records}, indent=2))
    for record in records:
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
