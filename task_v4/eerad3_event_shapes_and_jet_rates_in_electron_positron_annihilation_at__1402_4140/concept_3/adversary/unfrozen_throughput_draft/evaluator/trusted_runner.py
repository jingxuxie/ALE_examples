import base64
import ctypes
import json
import mmap
import os
import resource
import signal
import struct
import sys
import tempfile
import time


def deadline(signum, frame):
    raise TimeoutError('native executable or adopted descendant exceeded wrapper deadline')


def main():
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('cannot enable descendant CPU accounting')
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError('cannot protect trusted wrapper process')
    payload = sys.stdin.buffer.read(32 * 1024**2 + 1)
    if len(payload) > 32 * 1024**2:
        raise ValueError('Input batch exceeds bounded staging limit')
    if len(payload) < 16 or payload[:8] != b'ERAD3B4\0':
        raise ValueError('Invalid shared-buffer input header')
    count, reserved = struct.unpack_from('<II', payload, 8)
    if not 1 <= count <= 20000 or reserved != 0 or len(payload) != 16 + count * 224:
        raise ValueError('Invalid shared-buffer input size')
    with mmap.mmap(-1, len(payload), flags=mmap.MAP_SHARED) as inputs, \
            mmap.mmap(-1, 16 + count * 672, flags=mmap.MAP_SHARED) as output, tempfile.TemporaryFile() as errors:
        inputs[:] = payload
        output.write(b'ERAD3O4\0' + struct.pack('<II', count, 0))
        remaining = count * 672
        zeros = bytes(min(1024 ** 2, remaining))
        while remaining:
            block = min(remaining, len(zeros))
            output.write(zeros[:block])
            remaining -= block
        input_address = ctypes.addressof(ctypes.c_char.from_buffer(inputs))
        output_address = ctypes.addressof(ctypes.c_char.from_buffer(output))
        signal.signal(signal.SIGALRM, deadline)
        signal.alarm(55)
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        readiness_read, readiness_write = os.pipe2(os.O_CLOEXEC)
        process = os.fork()
        if process == 0:
            try:
                os.close(readiness_read)
                os.dup2(errors.fileno(), 1)
                os.dup2(errors.fileno(), 2)
                null_descriptor = os.open('/dev/null', os.O_RDONLY)
                os.dup2(null_descriptor, 0)
                os.close(null_descriptor)
                for offset in range(0, len(inputs), mmap.PAGESIZE):
                    inputs[offset]
                for offset in range(0, len(output), mmap.PAGESIZE):
                    output[offset] = output[offset]
                setup = resource.getrusage(resource.RUSAGE_SELF)
                os.write(readiness_write, struct.pack('<dd', setup.ru_utime, setup.ru_stime))
                os.close(readiness_write)
                native = ctypes.CDLL('/work/runner.so')
                native.eerad3_batch.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
                native.eerad3_batch.restype = None
                native.eerad3_batch(input_address, output_address, count)
                os._exit(0)
            except BaseException as error:
                os.write(2, (type(error).__name__ + ': ' + str(error)).encode(errors='replace'))
                os._exit(1)
        os.close(readiness_write)
        startup = os.read(readiness_read, 16)
        os.close(readiness_read)
        if len(startup) != 16:
            raise RuntimeError('Trusted pre-native startup record missing')
        setup_user_seconds, setup_system_seconds = struct.unpack('<dd', startup)
        _, status = os.waitpid(process, 0)
        returncode = os.waitstatus_to_exitcode(status)
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        full_user_seconds = after.ru_utime - before.ru_utime
        full_system_seconds = after.ru_stime - before.ru_stime
        user_seconds = full_user_seconds - setup_user_seconds
        system_seconds = full_system_seconds - setup_system_seconds
        duration = user_seconds + system_seconds
        wall_seconds = time.monotonic() - started
        output.seek(0)
        stdout = output.read(32 * 1024**2 + 1)
        if len(stdout) > 32 * 1024**2:
            raise ValueError('native output exceeds bounded log limit')
        errors.seek(max(0, errors.seek(0, os.SEEK_END) - 4000))
        stderr = errors.read().decode(errors='replace')
    signal.alarm(0)
    print(json.dumps({'cpu_seconds': duration, 'user_seconds': user_seconds, 'system_seconds': system_seconds,
                      'wall_seconds': wall_seconds, 'returncode': returncode,
                      'input_transport': 'fork-shared resident buffers; only trusted pre-load staging CPU excluded; candidate constructors and descendants counted',
                      'full_child_cpu_seconds': full_user_seconds + full_system_seconds,
                      'trusted_setup_cpu_seconds': setup_user_seconds + setup_system_seconds,
                      'minor_faults': after.ru_minflt - before.ru_minflt,
                      'major_faults': after.ru_majflt - before.ru_majflt,
                      'voluntary_context_switches': after.ru_nvcsw - before.ru_nvcsw,
                      'involuntary_context_switches': after.ru_nivcsw - before.ru_nivcsw,
                      'stdout_b64': base64.b64encode(stdout).decode('ascii'), 'stderr': stderr}, allow_nan=False))
    return 0 if returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
