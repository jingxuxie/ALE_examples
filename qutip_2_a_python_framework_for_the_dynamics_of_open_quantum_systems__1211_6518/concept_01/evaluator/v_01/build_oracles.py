import json
from pathlib import Path
import shutil

from evaluate import run_command, ROOT, HIDDEN


def main():
    destination = ROOT / 'solution/v_01/oracle_runs'
    (HIDDEN / 'oracles').mkdir(exist_ok=True)
    resources = {}
    for manifest in sorted(HIDDEN.glob('*.json')):
        if manifest.name == 'calibration.json':
            continue
        metadata = json.loads(manifest.read_text())
        case = metadata['id']
        output = destination / case
        metrics = run_command(['bash', str(ROOT / 'solution/v_01/output/run.sh'), 'solve', str(manifest),
                               str(output), '--config', 'refined'], output / 'resources')
        if metrics['returncode'] != 0:
            raise RuntimeError(case + ': ' + str(metrics))
        shutil.copyfile(output / 'result.npz', HIDDEN / 'oracles' / (case + '.npz'))
        resources[case] = metrics
    (ROOT / 'screening/v_01/oracle_resources.json').write_text(json.dumps(resources, indent=2))
    print(json.dumps(resources, indent=2))


if __name__ == '__main__':
    main()
