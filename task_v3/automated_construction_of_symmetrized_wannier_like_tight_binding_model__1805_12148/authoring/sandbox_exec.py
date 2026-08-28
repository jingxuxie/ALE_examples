import os
import pathlib
import resource
import shutil
import stat
import subprocess
import sys
import time


def run_submission(entrypoint, input_path, output_path, participant, timeout=180, memory_gib=8):
    entrypoint = pathlib.Path(entrypoint).absolute()
    if entrypoint.is_symlink() or not entrypoint.is_file():
        return {'returncode': 65, 'seconds': 0.0, 'peak_rss_kib': 0, 'log_tail': 'The submission entrypoint must be a regular, nonsymlink file.'}
    entrypoint = entrypoint.resolve()
    input_path = pathlib.Path(input_path).resolve()
    output_path = pathlib.Path(output_path).absolute()
    output_path = output_path.parent.resolve() / output_path.name
    participant = pathlib.Path(participant).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resource_path = output_path.parent / 'resources.txt'
    if not shutil.which('bwrap'):
        raise RuntimeError('bwrap is required; refusing unsandboxed evaluation')
    command = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev']
    for directory in ['/usr', '/bin', '/lib', '/lib64', '/etc/alternatives']:
        if pathlib.Path(directory).exists():
            command.extend(['--ro-bind', directory, directory])
    for filename in ['/etc/ld.so.cache', '/etc/localtime']:
        if pathlib.Path(filename).exists():
            command.extend(['--ro-bind', filename, filename])
    for directory in [participant, entrypoint.parent]:
        command.extend(['--ro-bind', str(directory), str(directory)])
    command.extend(['--ro-bind', str(input_path), str(input_path), '--bind', str(output_path.parent), str(output_path.parent), '--chdir', str(entrypoint.parent), '/usr/bin/time', '-v', '-o', str(resource_path), '/usr/bin/python3', str(entrypoint), '--input', str(input_path), '--output', str(output_path)])
    environment = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/tmp', 'TMPDIR': '/tmp', 'PYTHONNOUSERSITE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMBA_NUM_THREADS': '1'}
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (memory_gib * 1024 ** 3, memory_gib * 1024 ** 3))
    started = time.monotonic()
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=environment, timeout=timeout, preexec_fn=limits)
        log = process.stdout
        returncode = process.returncode
    except subprocess.TimeoutExpired as error:
        log = str(error.stdout or '') + '\nTIMEOUT'
        returncode = 124
    (output_path.parent / 'process.log').write_text(log)
    peak = None
    if resource_path.exists():
        for line in resource_path.read_text().splitlines():
            if 'Maximum resident set size (kbytes)' in line:
                peak = int(line.rsplit(':', 1)[1])
    if 'Creating new namespace failed' in log or 'Operation not permitted' in log and 'bwrap:' in log:
        raise RuntimeError('Evaluation isolation unavailable; rerun evaluator outside the parent sandbox, keeping bwrap enabled: ' + log[-1000:])
    if returncode == 0:
        try:
            output_stat = output_path.lstat()
            if not stat.S_ISREG(output_stat.st_mode) or output_stat.st_size > 512 * 1024 ** 2:
                returncode = 65
                log += '\nRejected nonregular, symlink or oversized output.'
        except FileNotFoundError:
            returncode = 65
            log += '\nNo output file was produced.'
    return {'returncode': returncode, 'seconds': time.monotonic() - started, 'peak_rss_kib': peak, 'log_tail': log[-2000:]}
