import json
import os
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'evaluator' / 'hidden' / 'manifest.json').read_text())
    outputs = root / 'screening' / 'reference_outputs'
    outputs.mkdir(exist_ok=True)
    resources = {}
    for entry in manifest:
        case_id = entry['case_id']
        destination = outputs / case_id
        destination.mkdir(exist_ok=True)
        environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                           PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
        environment.pop('PYTHONPATH', None)
        command = ['/usr/bin/time', '-f', '%e %M', '-o', str(destination / 'resources.txt'),
                   'bash', str(root / 'solution' / 'output' / 'run.sh'),
                   str(root / 'evaluator' / 'hidden' / 'cases' / entry['file']),
                   str(destination), '--mode', 'selected']
        subprocess.run(command, check=True, env=environment, cwd='/tmp', timeout=120)
        seconds, memory_kb = map(float, (destination / 'resources.txt').read_text().strip().split())
        resources[case_id] = dict(seconds=seconds, peak_rss_mb=memory_kb / 1024)
        (root / 'evaluator' / 'hidden' / 'resources.json').write_text(json.dumps(resources, indent=2) + '\n')
    print(json.dumps(resources, indent=2))


if __name__ == '__main__':
    main()
