import argparse
import ctypes
import json
import mmap
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time


def encode_cases(cases):
    payload = bytearray(b'ERAD3B4\0' + struct.pack('<II', len(cases), 0))
    for case in cases:
        payload.extend(struct.pack('<20d', *[value for vector in case['p'] for value in vector]))
    for name, layout in [('labels', '<5i'), ('slots', '<3i'), ('axis', '<4d')]:
        for case in cases:
            payload.extend(struct.pack(layout, *case[name]))
    return bytes(payload)


def decode_records(payload):
    if len(payload) < 16 or payload[:8] != b'ERAD3O4\0':
        raise ValueError('Invalid output header')
    count, reserved = struct.unpack_from('<II', payload, 8)
    if reserved != 0 or len(payload) != 16 + count * 672:
        raise ValueError('Invalid output length or reserved header word')
    return [struct.unpack_from('<84d', payload, 16 + 672 * index) for index in range(count)]


def run_binary(library_path, input_path, output_path):
    payload = input_path.read_bytes()
    if len(payload) < 16 or payload[:8] != b'ERAD3B4\0':
        raise ValueError('Invalid input header')
    count, reserved = struct.unpack_from('<II', payload, 8)
    if not 1 <= count <= 20000 or reserved != 0 or len(payload) != 16 + count * 224:
        raise ValueError('Invalid input count or length')
    output_size = 16 + 672 * count
    with mmap.mmap(-1, len(payload), flags=mmap.MAP_SHARED) as inputs, \
            mmap.mmap(-1, output_size, flags=mmap.MAP_SHARED) as output:
        inputs[:] = payload
        output[:] = b'ERAD3O4\0' + struct.pack('<II', count, 0) + bytes(672 * count)
        input_pointer = ctypes.addressof(ctypes.c_char.from_buffer(inputs))
        output_pointer = ctypes.addressof(ctypes.c_char.from_buffer(output))
        ready_read, ready_write = os.pipe2(os.O_CLOEXEC)
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        child = os.fork()
        if child == 0:
            try:
                os.close(ready_read)
                for offset in range(0, len(inputs), mmap.PAGESIZE):
                    inputs[offset]
                for offset in range(0, len(output), mmap.PAGESIZE):
                    output[offset] = output[offset]
                setup = resource.getrusage(resource.RUSAGE_SELF)
                os.write(ready_write, struct.pack('<dd', setup.ru_utime, setup.ru_stime))
                os.close(ready_write)
                kernel = ctypes.CDLL(str(library_path.resolve()))
                entry = kernel.eerad3_batch
                entry.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
                entry.restype = None
                entry(input_pointer, output_pointer, count)
                os._exit(0)
            except BaseException as error:
                print(str(error), file=sys.stderr, flush=True)
                os._exit(1)
        os.close(ready_write)
        startup = os.read(ready_read, 16)
        os.close(ready_read)
        deadline = time.monotonic() + 60
        while True:
            completed, status = os.waitpid(child, os.WNOHANG)
            if completed == child:
                break
            if time.monotonic() >= deadline:
                os.kill(child, signal.SIGKILL)
                os.waitpid(child, 0)
                raise TimeoutError('Local native library exceeded 60 seconds')
            time.sleep(0.01)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        if len(startup) != 16 or os.waitstatus_to_exitcode(status) != 0:
            raise RuntimeError('Native child failed or trusted setup record is missing')
        setup_user, setup_system = struct.unpack('<dd', startup)
        result = output[:]
        decode_records(result)
        output_path.write_bytes(result)
    full_user = after.ru_utime - before.ru_utime
    full_system = after.ru_stime - before.ru_stime
    user_seconds = full_user - setup_user
    system_seconds = full_system - setup_system
    print(json.dumps({'cpu_seconds': user_seconds + system_seconds,
                      'user_seconds': user_seconds, 'system_seconds': system_seconds,
                      'full_child_cpu_seconds': full_user + full_system,
                      'trusted_setup_cpu_seconds': setup_user + setup_system,
                      'note': 'local direct-child diagnostic, not an evaluator score'}), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['encode', 'decode', 'run'])
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--library', type=Path)
    arguments = parser.parse_args()
    if arguments.mode == 'encode':
        if arguments.output is None:
            parser.error('encode requires an output file')
        cases = json.loads(arguments.input.read_text())
        arguments.output.write_bytes(encode_cases(cases))
    elif arguments.mode == 'run':
        if arguments.library is None or arguments.output is None:
            parser.error('run requires --library and an output file')
        run_binary(arguments.library, arguments.input, arguments.output)
    else:
        records = decode_records(arguments.input.read_bytes())
        text = json.dumps(records, indent=2) + '\n'
        if arguments.output:
            arguments.output.write_text(text)
        else:
            print(text, end='')


if __name__ == '__main__':
    main()
