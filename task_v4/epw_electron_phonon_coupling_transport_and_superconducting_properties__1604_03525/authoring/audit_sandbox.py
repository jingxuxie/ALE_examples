import json
from pathlib import Path
import tempfile
from sandbox import run_submission


def main():
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='epw_sandbox_audit_') as temporary:
        base = Path(temporary)
        submission = base / 'submission'
        submission.mkdir()
        secret = base / 'hidden_secret.txt'
        secret.write_text('not-participant-data')
        input_path = base / 'input.npz'
        input_path.write_text('allowed-input')
        code = f'''import argparse,json,socket
from pathlib import Path
import numpy,scipy
parser=argparse.ArgumentParser()
parser.add_argument('--input');parser.add_argument('--output')
args=parser.parse_args()
denied=False
try: Path({str(secret)!r}).read_text()
except (PermissionError,FileNotFoundError): denied=True
network=False
try:
    connection=socket.create_connection(('1.1.1.1',443),timeout=1)
    connection.close()
except OSError: network=True
report={{'hidden_denied':denied,'network_denied':network,'input_read':Path(args.input).read_text()=='allowed-input','numpy':numpy.__version__,'scipy':scipy.__version__}}
Path(args.output).write_text(json.dumps(report))
assert denied and network and report['input_read']
'''
        (submission / 'solve.py').write_text(code)
        output = base / 'output'
        runtime = run_submission(submission, input_path, output, timeout=20, output_name='audit.json')
        report = {'runtime': runtime, 'passed': runtime['returncode'] == 0 and not runtime['timed_out']}
        if (output / 'audit.json').exists():
            report.update(json.loads((output / 'audit.json').read_text()))
        (root / 'sandbox_audit.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
        if not report['passed']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
