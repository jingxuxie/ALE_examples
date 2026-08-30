"""Audit evaluator readiness, solver-only deadlines, and descendant cleanup."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from isolation import AUTHORING, private_directory, run_evaluation
from sandbox import run_file


SOLVER = r'''
import argparse
import json
import os
from pathlib import Path
import time
parser = argparse.ArgumentParser()
parser.add_argument('--input')
parser.add_argument('--output')
args = parser.parse_args()
request = json.loads(Path(args.input).read_text())
inherited = []
for name in os.listdir('/proc/self/fd'):
    descriptor = int(name)
    if descriptor > 2:
        try:
            os.fstat(descriptor)
            inherited.append(descriptor)
        except OSError:
            pass
print(json.dumps({'pid_namespace': os.readlink('/proc/self/ns/pid')}), flush=True)
if request.get('spawn') and os.fork() == 0:
    os.setsid()
    time.sleep(30)
    os._exit(0)
time.sleep(request['sleep'])
Path(args.output).write_text(json.dumps({'inherited_fds': inherited}))
'''


def namespace_exists(namespace):
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                if os.readlink(entry / 'ns/pid') == namespace:
                    return True
            except OSError:
                pass
    return False


def main():
    report = {'date': datetime.now(timezone.utc).isoformat(), 'model_calls': 0}
    with private_directory('audit_timing_') as directory:
        root = Path(directory)
        participant = root / 'participant'
        submission = root / 'submission'
        participant.mkdir()
        submission.mkdir()
        (submission / 'solve.py').write_text(SOLVER)
        current = root / 'input.json'
        current.write_text(json.dumps({'sleep': 0.2}))
        answer, telemetry = run_file(submission, participant, current, timeout=2)
        report['solver_budget_after_setup'] = {
            'passed': answer == {'inherited_fds': []} and not telemetry['timed_out']
                      and telemetry['ready_received'] and telemetry['elapsed_seconds'] < 2,
            'answer': answer, 'telemetry': telemetry}
        print('solver-only budget and closed ready FD: ' + str(report['solver_budget_after_setup']['passed']), flush=True)
        current.write_text(json.dumps({'sleep': 5, 'spawn': True}))
        answer, telemetry = run_file(submission, participant, current, timeout=0.4)
        namespace = json.loads(telemetry['stdout'].splitlines()[0])['pid_namespace'] if telemetry['stdout'] else None
        if namespace:
            for attempt in range(20):
                if not namespace_exists(namespace):
                    break
                time.sleep(0.1)
        report['timeout_and_descendant_cleanup'] = {
            'passed': answer is None and telemetry['timed_out'] and not telemetry['setup_timed_out']
                      and bool(namespace) and not namespace_exists(namespace),
            'telemetry': telemetry}
        print('solver timeout and detached descendant cleanup: ' + str(report['timeout_and_descendant_cleanup']['passed']), flush=True)
        telemetry = run_evaluation({'mounts': [], 'cwd': '/', 'evaluation': True,
                                    'memory_mb': 2048, 'timeout': 45, 'command': ['/bin/true']},
                                   environment={'PATH': '/usr/bin:/bin'}, timeout=45,
                                   max_output_bytes=4096, setup_timeout=0.001)
        report['setup_failure_is_infrastructure'] = {
            'passed': telemetry['setup_timed_out'] and not telemetry['timed_out']
                      and not telemetry['ready_received'] and bool(telemetry['infrastructure_error']),
            'telemetry': telemetry}
    report['passed'] = all(result['passed'] for result in report.values() if isinstance(result, dict))
    path = AUTHORING / 'timing_audit.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print('Timing audit passed: ' + str(report['passed']) + '; ' + str(path), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
