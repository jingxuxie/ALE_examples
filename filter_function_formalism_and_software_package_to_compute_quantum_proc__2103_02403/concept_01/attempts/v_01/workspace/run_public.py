import datetime
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    launches = []
    for path in sorted((ROOT / 'input' / 'cases').glob('*.json')):
        case = json.loads(path.read_text())
        for mode in ['selected', 'baseline', 'refined', 'no_memory']:
            row_id = f"{case['case_id']}_{mode}"
            destination = ROOT / 'artifacts' / row_id
            if (destination / 'metrics.json').exists():
                snapshot = ROOT / 'iterations' / 'pre_final' / row_id
                snapshot.mkdir(parents=True, exist_ok=True)
                for filename in ['metrics.json', 'process.npz']:
                    shutil.copy2(destination / filename, snapshot / filename)
            command = ['bash', str(ROOT / 'run.sh'), str(path), str(destination), '--mode', mode]
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            started = time.perf_counter()
            completed = subprocess.run(command, cwd=ROOT / 'workspace', text=True,
                                       capture_output=True, timeout=110)
            wall = time.perf_counter() - started
            (ROOT / 'logs' / (row_id + '_final.log')).write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise RuntimeError(f'{row_id}: {completed.stderr}')
            launch = dict(row_id=row_id, case_id=case['case_id'], mode=mode,
                          artifact=str(destination.relative_to(ROOT)), wall_seconds=wall,
                          started_utc=timestamp, command=command, returncode=completed.returncode)
            launches.append(launch)
            (ROOT / 'launches.json').write_text(json.dumps(launches, indent=2) + '\n')
            print(json.dumps(launch), flush=True)
    manifest = {}
    for path in sorted((ROOT / 'input').rglob('*')):
        if path.is_file():
            manifest[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((ROOT / 'workspace' / 'pipeline').glob('*.py')):
        manifest[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
