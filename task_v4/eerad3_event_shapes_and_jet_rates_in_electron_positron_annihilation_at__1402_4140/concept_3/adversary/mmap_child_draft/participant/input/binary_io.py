import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys


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


def run_binary(executable, input_path, output_path):
    payload = input_path.read_bytes()
    if len(payload) < 16 or payload[:8] != b'ERAD3B4\0':
        raise ValueError('Invalid input header')
    count, reserved = struct.unpack_from('<II', payload, 8)
    if not 1 <= count <= 20000 or reserved != 0 or len(payload) != 16 + count * 224:
        raise ValueError('Invalid input count or length')
    input_descriptor = os.memfd_create('mapping-input', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    output_descriptor = os.memfd_create('mapping-output', os.MFD_CLOEXEC)
    with os.fdopen(input_descriptor, 'w+b') as inputs, os.fdopen(output_descriptor, 'w+b') as output:
        inputs.write(payload)
        inputs.flush()
        inputs.seek(0)
        fcntl.fcntl(inputs.fileno(), fcntl.F_ADD_SEALS,
                    fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        output.write(b'ERAD3O4\0' + struct.pack('<II', count, 0) + bytes(672 * count))
        output.flush()
        output.seek(0)
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        subprocess.run([str(executable.resolve())], stdin=inputs, stdout=output, check=True, timeout=60)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        output.seek(0)
        result = output.read(16 + 672 * count + 1)
        decode_records(result)
        output_path.write_bytes(result)
    user_seconds = after.ru_utime - before.ru_utime
    system_seconds = after.ru_stime - before.ru_stime
    print(json.dumps({'cpu_seconds': user_seconds + system_seconds,
                      'user_seconds': user_seconds, 'system_seconds': system_seconds,
                      'note': 'local direct-child diagnostic, not an evaluator score'}), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['encode', 'decode', 'run'])
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--executable', type=Path)
    arguments = parser.parse_args()
    if arguments.mode == 'encode':
        if arguments.output is None:
            parser.error('encode requires an output file')
        cases = json.loads(arguments.input.read_text())
        arguments.output.write_bytes(encode_cases(cases))
    elif arguments.mode == 'run':
        if arguments.executable is None or arguments.output is None:
            parser.error('run requires --executable and an output file')
        run_binary(arguments.executable, arguments.input, arguments.output)
    else:
        records = decode_records(arguments.input.read_bytes())
        text = json.dumps(records, indent=2) + '\n'
        if arguments.output:
            arguments.output.write_text(text)
        else:
            print(text, end='')


if __name__ == '__main__':
    main()
