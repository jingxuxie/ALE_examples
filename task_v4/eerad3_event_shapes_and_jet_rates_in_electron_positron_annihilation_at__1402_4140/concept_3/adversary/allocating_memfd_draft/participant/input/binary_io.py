import argparse
import json
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['encode', 'decode'])
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    arguments = parser.parse_args()
    if arguments.mode == 'encode':
        if arguments.output is None:
            parser.error('encode requires an output file')
        cases = json.loads(arguments.input.read_text())
        payload = bytearray(b'ERAD3B3\0' + struct.pack('<I', len(cases)))
        for case in cases:
            payload.extend(struct.pack('<20d', *[value for vector in case['p'] for value in vector]))
        for name, layout in [('labels', '<5i'), ('slots', '<3i'), ('axis', '<4d')]:
            for case in cases:
                payload.extend(struct.pack(layout, *case[name]))
        arguments.output.write_bytes(payload)
    else:
        payload = arguments.input.read_bytes()
        if len(payload) < 12 or payload[:8] != b'ERAD3O3\0':
            raise ValueError('Invalid output header')
        count = struct.unpack_from('<I', payload, 8)[0]
        if len(payload) != 12 + count * 672:
            raise ValueError('Invalid output length')
        records = [struct.unpack_from('<84d', payload, 12 + 672 * index) for index in range(count)]
        text = json.dumps(records, indent=2) + '\n'
        if arguments.output:
            arguments.output.write_text(text)
        else:
            print(text, end='')


if __name__ == '__main__':
    main()
