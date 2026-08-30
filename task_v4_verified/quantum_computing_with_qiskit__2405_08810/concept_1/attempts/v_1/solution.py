#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
import time


DIRECTORY = Path(__file__).resolve().parent
ENGINE = DIRECTORY / 'engine'


def fallback(instance):
    from reference import Compiler, simplify
    compiler = Compiler(instance)
    operations = []
    for term, mask in enumerate(instance['terms']):
        unused, gates, root = compiler.plan(mask)
        operations.extend(['cx', control, target] for control, target in gates)
        operations.append(['rz', root, term])
        operations.extend(['cx', control, target] for control, target in reversed(gates))
    operations = simplify(operations)
    if not any(operation[0] == 'cx' for operation in operations):
        control, target, unused, unused_duration = min(instance['edges'], key=lambda edge: edge[2] + 0.2 * edge[3])
        operations.extend([['cx', control, target], ['cx', control, target]])
    return {'ops': operations}


def compile_circuit(instance):
    started = time.monotonic()
    try:
        if not ENGINE.is_file() or not os.access(ENGINE, os.X_OK):
            temporary = DIRECTORY / '.engine_build'
            subprocess.run(['g++', '-O3', '-std=c++17', str(DIRECTORY / 'engine.cpp'), '-o', str(temporary)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=4.0)
            os.replace(temporary, ENGINE)
        remaining = 12.0 - (time.monotonic() - started)
        if remaining < 1.0:
            return fallback(instance)
        budget = min(8.3, remaining - 0.6)
        values = [instance['n'], len(instance['edges']), len(instance['terms'])]
        values.extend(value for edge in instance['edges'] for value in edge)
        values.extend(instance['terms'])
        process = subprocess.run([str(ENGINE), str(budget)], input=' '.join(map(str, values)), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True, timeout=remaining)
        response = json.loads(process.stdout)
        if type(response) is not dict or set(response) != {'ops'}:
            return fallback(instance)
        return response
    except (OSError, subprocess.SubprocessError, ValueError):
        return fallback(instance)


def main():
    for line in sys.stdin:
        if line.strip():
            response = compile_circuit(json.loads(line))
            print(json.dumps(response, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
