import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import time


def safe_tree(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('submission must be a real directory')
    for path in directory.rglob('*'):
        information = path.lstat()
        if stat.S_ISLNK(information.st_mode) or not (stat.S_ISREG(information.st_mode) or stat.S_ISDIR(information.st_mode)):
            raise ValueError('links and special files are not permitted')
        if stat.S_ISREG(information.st_mode) and information.st_nlink != 1:
            raise ValueError('hardlinked submission file')
    if not (directory / 'solve.py').is_file():
        raise ValueError('submission needs solve.py')


def command(submission, workspace, input_directory, output_directory):
    arguments = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL']
    for directory in ['/usr', '/lib', '/lib64', '/etc/alternatives', '/etc/ld.so.cache']:
        arguments.extend(['--ro-bind', directory, directory])
    arguments.extend(['--symlink', 'usr/bin', '/bin', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                      '--dir', '/home', '--ro-bind', str(submission), '/submission',
                      '--ro-bind', str(workspace), '/workspace', '--ro-bind', str(input_directory), '/input',
                      '--bind', str(output_directory), '/output', '--chdir', '/output', '--clearenv'])
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp', 'LANG': 'C.UTF-8',
                   'PYTHONPATH': '/workspace', 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                   'OPENBLAS_NUM_THREADS': '4', 'OMP_NUM_THREADS': '4', 'OMP_THREAD_LIMIT': '4',
                   'MKL_NUM_THREADS': '4', 'NUMEXPR_NUM_THREADS': '4', 'CUDA_VISIBLE_DEVICES': ''}
    for name, value in environment.items():
        arguments.extend(['--setenv', name, value])
    arguments.extend(['/usr/bin/python3', '-B', '-s', '/submission/solve.py', '--input', '/input', '--output', '/output/solution.json'])
    return arguments


def replay(submission, workspace, input_directory, output_directory, seconds=90):
    safe_tree(submission)
    output_directory = Path(output_directory)
    output_directory.mkdir()
    allowed_cpus = sorted(os.sched_getaffinity(0))[:4]

    def limits():
        os.sched_setaffinity(0, allowed_cpus)
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (4 * seconds, 4 * seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 ** 2,) * 2)
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.monotonic()
    with (output_directory.parent / 'stdout.log').open('wb') as stdout, (output_directory.parent / 'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command(Path(submission).resolve(), Path(workspace).resolve(), Path(input_directory).resolve(), output_directory.resolve()),
                                   stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True,
                                   env={'PATH': '/usr/bin:/bin'}, start_new_session=True, preexec_fn=limits)
        timed_out = False
        try:
            process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    record = {'wall_seconds': time.monotonic() - started, 'wall_limit_seconds': seconds,
              'returncode': process.returncode, 'timed_out': timed_out, 'cpu_affinity': allowed_cpus,
              'address_space_limit_bytes': 2 * 1024 ** 3, 'isolated': True}
    if timed_out or process.returncode != 0:
        record['error'] = 'wall timeout' if timed_out else 'isolated process failed'
        return None, record
    result_path = output_directory / 'solution.json'
    descriptor = os.open(result_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1 or information.st_size > 65536:
            raise ValueError('result must be a regular unlinked JSON file at most 64 KiB')
        result = json.load(stream)
    return result, record
