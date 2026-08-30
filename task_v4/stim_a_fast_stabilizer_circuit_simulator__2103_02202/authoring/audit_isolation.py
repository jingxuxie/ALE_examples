"""Credential-free plain-process audits. This file never invokes codex exec."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys

from isolation import AUTHORING, private_directory, run_isolated
from launch import RUNNER, RUNNER_SHA256, controller_environment, digest, fresh_runtime, generation_spec, sandbox_command
from sandbox import run_file


PROBE = r'''
import argparse
import ctypes
import json
import os
from pathlib import Path
import resource
import socket
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--input')
parser.add_argument('--output')
args = parser.parse_args()
request = json.loads(Path(args.input).read_text())
checks = {}
def unreadable(path):
    try:
        Path(path).read_bytes()
        return False
    except OSError:
        return True
def unwritable(path):
    try:
        with open(path, 'ab') as stream:
            stream.write(b'forbidden')
        return False
    except OSError:
        return True
checks['hidden_paths_unreadable'] = all(unreadable(path) for path in request['hidden'])
checks['proc_root_hidden_unreadable'] = all(unreadable(prefix + path)
    for prefix in ('/proc/1/root', '/proc/self/root') for path in request['hidden'])
checks['host_process_unreadable'] = unreadable('/proc/' + str(request['host_pid']) + '/environ')
checks['participant_read_only'] = unwritable(request['participant'] + '/public.txt')
checks['public_readable'] = Path(request['participant'] + '/public.txt').read_text() == 'public'
checks['no_parent_credentials'] = not any('KEY' in name or 'TOKEN' in name or 'SECRET' in name for name in os.environ)
checks['oldroot_absent'] = not Path('/oldroot').exists()
try:
    connection = socket.socket()
    connection.settimeout(0.2)
    connection.connect(('127.0.0.1', request['port']))
    checks['host_network_blocked'] = False
    connection.close()
except OSError:
    checks['host_network_blocked'] = True
if request['evaluation']:
    import numpy
    import scipy
    import public_module
    checks['public_import'] = public_module.VALUE == 17
    checks['pythonpath_exact'] = os.environ['PYTHONPATH'] == '/task/workspace:/submission'
    checks['one_cpu'] = len(os.sched_getaffinity(0)) == 1
    checks['memory_limit'] = resource.getrlimit(resource.RLIMIT_AS) == (2048 * 1024**2,) * 2
    checks['single_input_mount'] = sorted(path.name for path in Path('/input').iterdir()) == ['instance.json']
    checks['aliases_present'] = Path(request['submission'] + '/solve.py').read_bytes() == Path('/submission/solve.py').read_bytes()
    checks['submission_read_only'] = unwritable('/submission/solve.py')
    checks['zero_capabilities'] = all(line.split()[1] == '0000000000000000' for line in Path('/proc/self/status').read_text().splitlines() if line.startswith(('CapEff:', 'CapPrm:', 'CapBnd:')))
    checks['mount_blocked'] = ctypes.CDLL(None).mount(None, b'/', None, 32, None) != 0
    compiled = subprocess.run(['/usr/bin/c++', '-x', 'c++', '-o', '/work/compiler_probe', '-'], input=b'int main(){return 0;}\n', capture_output=True)
    checks['compiler_works'] = compiled.returncode == 0 and subprocess.run(['/work/compiler_probe']).returncode == 0
    checks['numpy_scipy_work'] = int(numpy.arange(4).sum()) == 6 and bool(scipy.__version__)
Path(args.output).write_text(json.dumps(checks))
print(json.dumps(checks), flush=True)
'''


def fixture(root, port):
    participant = root / 'participant'
    submission = root / 'attempts/v_1'
    hidden = root / 'hidden'
    (participant / 'workspace').mkdir(parents=True)
    submission.mkdir(parents=True)
    hidden.mkdir()
    (participant / 'public.txt').write_text('public')
    (participant / 'workspace/public_module.py').write_text('VALUE = 17\n')
    (hidden / 'sibling.json').write_text('{"hidden_canary":true}')
    (hidden / 'evaluator.py').write_text('PRIVATE_CANARY = True\n')
    request = {'participant': str(participant), 'submission': str(submission), 'port': port,
               'host_pid': os.getpid(),
               'hidden': [str(hidden / 'sibling.json'), str(hidden / 'evaluator.py'),
                          '/home/xuandong/.codex/auth.json', '/srv/home/xuandong/.codex/auth.json'],
               'evaluation': True}
    (hidden / 'current.json').write_text(json.dumps(request))
    return participant, submission, hidden, request


def evaluation_probe(port):
    with private_directory('audit_eval_') as directory:
        participant, submission, hidden, request = fixture(Path(directory), port)
        (submission / 'solve.py').write_text(PROBE)
        request['hidden'].append(str(hidden / 'current.json'))
        (hidden / 'current.json').write_text(json.dumps(request))
        descriptor = os.open(hidden / 'evaluator.py', os.O_RDONLY)
        os.set_inheritable(descriptor, True)
        try:
            answer, telemetry = run_file(submission, participant, hidden / 'current.json')
        finally:
            os.close(descriptor)
        return {'passed': bool(answer) and all(answer.values()), 'checks': answer, 'telemetry': telemetry}


def generation_probe(port):
    with private_directory('audit_generation_') as directory:
        root = Path(directory)
        participant, output, hidden, request = fixture(root, port)
        runtime = root / 'runtime'
        fresh_runtime(runtime, audit=True)
        request.update(evaluation=False)
        request['hidden'].extend([str(runtime / 'auth.json'), str(runtime / 'config.toml')])
        (participant / 'probe.py').write_text(PROBE)
        (participant / 'request.json').write_text(json.dumps(request))
        spec = generation_spec(participant, output, runtime, 'UNUSED: audit never executes this prompt')
        runner_arguments = spec['command']
        spec['command'] = sandbox_command(participant, output, runtime,
            ['/usr/bin/python3', '-B', str(participant / 'probe.py'), '--input',
             str(participant / 'request.json'), '--output', str(output / 'answer.json')])
        telemetry = run_isolated(spec, environment=controller_environment(runtime, audit=True), timeout=60)
        answer = json.loads((output / 'answer.json').read_text()) if (output / 'answer.json').is_file() else {}
        return {'passed': bool(answer) and all(answer.values()) and telemetry['returncode'] == 0,
                'checks': answer, 'telemetry': telemetry,
                'fixed_model_effort': runner_arguments[1:5] == ['--model', 'ultima-alpha', '--effort', 'xhigh'],
                'task_read_only': runner_arguments[5] == '--task-read-only',
                'runner_unchanged': digest(RUNNER) == RUNNER_SHA256}


def baseline_probe():
    participant = AUTHORING.parent / 'concept_1/participant'
    answer, telemetry = run_file(participant / 'baseline', participant, participant / 'input/biased_0.json')
    return {'passed': answer is not None and telemetry['returncode'] == 0, 'telemetry': telemetry}


def main():
    report = {'date': datetime.now(timezone.utc).isoformat(), 'model_calls': 0}
    path = AUTHORING / 'isolation_audit.json'
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        port = listener.getsockname()[1]
        with ThreadPoolExecutor(max_workers=3) as executor:
            jobs = {'generation': executor.submit(generation_probe, port),
                    'evaluation': executor.submit(evaluation_probe, port),
                    'public_baseline': executor.submit(baseline_probe)}
            for name, job in jobs.items():
                try:
                    report[name] = job.result()
                except Exception as error:
                    report[name] = {'passed': False, 'error': str(error)}
                path.write_text(json.dumps(report, indent=2) + '\n')
                print(name + ': ' + ('PASS' if report[name]['passed'] else 'FAIL'), flush=True)
    report['passed'] = all(report[name]['passed'] for name in ('generation', 'evaluation', 'public_baseline'))
    path.write_text(json.dumps(report, indent=2) + '\n')
    print('Audit report: ' + str(path), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
