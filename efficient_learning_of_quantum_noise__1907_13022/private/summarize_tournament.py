from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONCEPTS = ['concept_01_sparse','concept_02_gateset','concept_03_experiment','concept_04_graphical']


def read(path):
    return json.loads(path.read_text())


def mean_score(report):
    for key in ['mean_core','mean_challenge','mean_selected','mean_score','mean']:
        value = report.get(key)
        if isinstance(value,(float,int)):
            return value
    raise ValueError('Missing aggregate score')


def numerical_runtime(report):
    return next((report[key] for key in ['runtime_seconds','runtime','total_seconds'] if key in report),None)


def main():
    records = []
    for concept in CONCEPTS:
        directory = ROOT/concept
        run = read(ROOT/'private'/'runs'/'pilot'/f'{concept}.json')
        assert run['model'] == 'ultima-alpha'
        assert run['solver_exists'] and run['participant_unchanged']
        assert run['returncode'] == 0 and not run['timed_out']
        assert run['seconds'] < 3600
        frozen = ROOT/'private'/'runs'/'pilot'/'submissions'/f'{concept}.py'
        assert hashlib.sha256(frozen.read_bytes()).hexdigest() == run['submission_sha256']
        pools = {}
        for pool in ['core','challenge']:
            report = read(ROOT/'private'/'scores'/'pilot'/f'{concept}_{pool}.json')
            pools[pool] = dict(mean=mean_score(report),worst_family=report['worst_family'],
                               families=report['families'],cases=len(report['cases']),
                               numerical_seconds=numerical_runtime(report),
                               case_minimum=min(row['score'] for row in report['cases']),
                               error_cases=[row for row in report['cases'] if row.get('error') or row.get('status')=='error'])
        reference_directory = directory/'private'/'reference'
        if concept == 'concept_01_sparse':
            verification = read(reference_directory/'verification.json')['pools']['core']
            reference_mean = verification['strong_mean']
            baseline_mean = verification['weak_mean']
        else:
            names = {'concept_02_gateset':('reference_core.json','baseline_core.json'),
                     'concept_03_experiment':('reference_score.json','baseline_score.json'),
                     'concept_04_graphical':('strong_core.json','weak_core.json')}[concept]
            reference_mean = mean_score(read(reference_directory/names[0]))
            baseline_mean = mean_score(read(reference_directory/names[1]))
        assert reference_mean > .9
        changed = []
        missing = []
        for relative, expected in run['private_sha256_before_attempt'].items():
            path = directory/'private'/relative
            if not path.is_file():
                missing.append(relative)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                changed.append(relative)
        records.append(dict(concept=concept,model=run['model'],model_seconds=run['seconds'],
                            model_minutes=run['seconds']/60,reference_mean=reference_mean,
                            weak_baseline_mean=baseline_mean,submission_sha256=run['submission_sha256'],
                            participant_unchanged=True,pools=pools,
                            prelaunch_private_files_changed=changed,
                            prelaunch_private_files_missing=missing))
    result = dict(status='initial_tournament_complete',
                  generated_utc=datetime.now(timezone.utc).isoformat(),concept_count=len(records),
                  model_attempt_count=len(records),pilot_time_limit_seconds=3600,
                  model='ultima-alpha',records=records)
    (ROOT/'private'/'tournament_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    for record in records:
        print(record['concept'],f"reference={record['reference_mean']:.9f}",
              f"core={record['pools']['core']['mean']:.9f}",
              f"worst={record['pools']['core']['worst_family']:.9f}",
              f"challenge={record['pools']['challenge']['mean']:.9f}",
              f"minutes={record['model_minutes']:.2f}",
              'private_changes=',record['prelaunch_private_files_changed'])


if __name__ == '__main__':
    main()
