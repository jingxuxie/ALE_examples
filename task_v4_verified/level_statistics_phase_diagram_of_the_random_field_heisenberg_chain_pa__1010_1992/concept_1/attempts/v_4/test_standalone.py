import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from test_submission import restrict


def main():
    assets = ['predict.py', 'model.pkl.gz', 'native_features.py', 'libnative_features.so',
              'transforms.py', 'fast_transform.so']
    source = Path(__file__).resolve().parent
    environment = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(dir=source, prefix='standalone_test_') as temporary:
        directory = Path(temporary)
        for asset in assets:
            shutil.copyfile(source / asset, directory / asset)
        cases = [json.loads(line) for line in (source / 'runtime_cases.jsonl').read_text().splitlines()]
        payload = {'cases': [{'id': case['id'], 'L': 14, 'fields': case['fields']} for case in cases]}
        process = subprocess.Popen([sys.executable, str(directory / 'predict.py')], cwd=os.environ['SRC'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=environment, preexec_fn=restrict)
        assert process.stdout.readline() == 'READY\n'
        started = time.monotonic()
        stdout, stderr = process.communicate(json.dumps(payload) + '\n', timeout=3)
        elapsed = time.monotonic() - started
        assert process.returncode == 0, stderr
        predictions = json.loads(stdout)['predictions']
        assert len(predictions) == len(cases) == 320
        assert {prediction['id'] for prediction in predictions} == {case['id'] for case in cases}
        result = {'self_contained': True, 'runtime_assets': assets, 'inference_seconds': elapsed,
                  'case_count': len(cases), 'stderr': stderr}
        (source / 'standalone_test.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
