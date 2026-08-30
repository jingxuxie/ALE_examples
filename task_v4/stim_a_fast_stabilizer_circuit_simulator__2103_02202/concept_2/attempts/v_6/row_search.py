import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
with (OUT / 'row_search.log').open('w') as log:
    for row in range(192):
        for value in (1, 0):
            if (OUT / 'success.json').exists():
                raise SystemExit
            result = subprocess.run([str(OUT / 'final_search'), '2', '192', '10', '8', str(7382903 + row * 127 + value), str(row), str(value)], cwd=OUT, stdout=log, stderr=log)
            print('row', row, 'value', value, 'status', result.returncode, flush=True)
