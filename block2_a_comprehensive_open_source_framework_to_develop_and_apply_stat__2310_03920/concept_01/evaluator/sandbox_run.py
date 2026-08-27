import os
from pathlib import Path
import signal
import subprocess
import time
import psutil


def execute(submission, assets, case_path, output, profile='production', timeout=180):
    submission, assets, case_path, output = [Path(path).resolve() for path in (submission, assets, case_path, output)]
    output.mkdir(parents=True, exist_ok=True)
    command = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
               '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin',
               '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
               '--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache', '--dev', '/dev', '--proc', '/proc',
               '--tmpfs', '/tmp', '--ro-bind', str(submission), '/submission',
               '--ro-bind', str(assets), '/assets', '--ro-bind', str(case_path), '/case.json',
               '--bind', str(output), '/work', '--chdir', '/work',
               '--setenv', 'ALE_ASSETS', '/assets', '--setenv', 'HOME', '/tmp',
               '--setenv', 'OPENBLAS_NUM_THREADS', '1', '--setenv', 'OMP_NUM_THREADS', '2',
               '--setenv', 'MKL_NUM_THREADS', '2', '--unsetenv', 'PYTHONPATH', '--unsetenv', 'LD_PRELOAD',
               '/bin/bash', '/submission/run.sh', '/case.json', '/work', profile]
    aliases = {str(assets), str(submission)}
    aliases.update(path.replace('/srv/home/', '/home/', 1) for path in list(aliases) if path.startswith('/srv/home/'))
    aliases.update(path.replace('/home/', '/srv/home/', 1) for path in list(aliases) if path.startswith('/home/'))
    for alias in sorted(aliases):
        source = assets if alias.endswith('participant/v_01') else submission
        command[1:1] = ['--ro-bind', str(source), alias]
    start = time.perf_counter()
    peak_mb, status = 0.0, 'ok'
    with (output / 'execution.log').open('w') as handle:
        process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            available = sorted(os.sched_getaffinity(0))
            utilization = psutil.cpu_percent(interval=0.1, percpu=True)
            physical_pool = available[:max(2, len(available) // 2)]
            selected = sorted(physical_pool, key=lambda core: utilization[core])[:2]
            os.sched_setaffinity(process.pid, selected)
        except (ProcessLookupError, OSError):
            pass
        monitor = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                processes = [monitor] + monitor.children(recursive=True)
                memory = sum(worker.memory_info().rss for worker in processes if worker.is_running()) / (1024 ** 2)
                peak_mb = max(peak_mb, memory)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            if time.perf_counter() - start > timeout:
                status = 'timeout'
            elif peak_mb > 4096:
                status = 'memory_limit'
            if status != 'ok':
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(0.15)
        returncode = process.wait()
    if returncode != 0 and status == 'ok':
        status = 'execution_error'
    return {'status': status, 'returncode': returncode, 'seconds': time.perf_counter() - start, 'peak_rss_mb': peak_mb}
