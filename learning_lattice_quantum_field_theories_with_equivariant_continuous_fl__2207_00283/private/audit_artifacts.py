import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024**2), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def git(repository, *arguments):
    return subprocess.check_output(['git', '-C', str(repository), *arguments], text=True).strip()


def main():
    source = HERE / 'sources'
    sources = {}
    for name in ('continuous-flow-lft', 'bijx'):
        repository = source / name
        sources[name] = {'commit': git(repository, 'rev-parse', 'HEAD'),
                         'commit_date': git(repository, 'show', '-s', '--format=%cI', 'HEAD'),
                         'origin': git(repository, 'remote', 'get-url', 'origin'),
                         'tags': git(repository, 'tag').splitlines(),
                         'tracked_diff': git(repository, 'diff', '--stat')}
    archives = {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
                for path in source.iterdir() if path.is_file() and path.suffix in ('.pdf', '.zip', '.json')}
    (HERE / 'source_manifest.json').write_text(json.dumps({'audit_date': '2026-08-28', 'repositories': sources, 'archives': archives}, indent=2))
    public = {}
    for pilot in sorted((ROOT / 'pilots').iterdir()):
        if not pilot.is_dir():
            continue
        participant = pilot / 'participant'
        paths = sorted(path for path in participant.rglob('*') if path.is_file()
                       and 'runtime' not in path.relative_to(participant).parts
                       and '__pycache__' not in path.parts)
        public[pilot.name] = {'files': {str(path.relative_to(participant)): digest(path) for path in paths},
                              'task_mentions_paper': '2207.00283' in (participant / 'TASK.md').read_text()
                              or 'Learning Lattice Quantum' in (participant / 'TASK.md').read_text()}
    (HERE / 'public_artifact_audit.json').write_text(json.dumps(public, indent=2))
    gauge = ROOT / 'pilots/03_gauge_transport/private'
    if (gauge / 'reference/dense_output.npz').exists():
        with np.load(gauge / 'reference/dense_output.npz') as archive:
            output = dict(archive)
        with np.load(gauge / 'reference/initial/su3_forward.reference.npz') as archive:
            target = dict(archive)
        manifest = json.loads((gauge / 'reference/initial/manifest.json').read_text())
        item = next(item for item in manifest if item['id'] == 'su3_forward')
        errors = {name: float(np.sqrt(np.mean(np.abs(output[name] - target[name])**2))) / item['weak_error'][name]
                  for name in output}
        scores = {name: 1 / (1 + 9 * np.sqrt(value)) for name, value in errors.items()}
        report = {'normalized_errors': errors, 'component_scores': scores,
                  'mean_core_with_unimplemented_components_zero': sum(scores.values()) / 6,
                  'notes': 'Dense all-coordinate Hessian; 16 exponential Euler steps; no sensitivities. Timings and memory are measured in dense_baseline.log, not inferred.'}
        (gauge / 'reference/dense_baseline_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'sources': sources, 'public_files': {name: len(record['files']) for name, record in public.items()}}, indent=2))


if __name__ == '__main__':
    main()
