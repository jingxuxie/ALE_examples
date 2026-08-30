#!/usr/bin/env python3
"""JSONL entry point. The task supplies a fresh local input/simulator.py."""
import os
import time
STARTED = time.monotonic()
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
import json
import gc
import ctypes
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / 'input'))
from calibration import Strategy


def main():
    strategy = Strategy()
    strategy.deadline = STARTED + 32.0
    for line in sys.stdin:
        message = json.loads(line)
        if time.monotonic() > STARTED + 39.0:
            result = strategy.current_estimate()
        else:
            try:
                result = strategy.next(message)
            except Exception:
                # Preserve a valid response if a numerical routine fails.
                result = strategy.current_estimate()
            if (result['type'] == 'experiment' and len(strategy.history) >= 18
                    and time.monotonic() > strategy.deadline):
                result = strategy.current_estimate()
        if result['type'] == 'estimate':
            result = strategy.current_estimate()
            payload = (json.dumps(result, allow_nan=False) + "\n").encode()
            # Release the numerical workspace BEFORE publishing the terminal
            # response, so process teardown is small and prompt even under load.
            del strategy
            gc.collect()
            try:
                trim = ctypes.CDLL(None).malloc_trim
                trim.argtypes = [ctypes.c_size_t]
                trim(0)
            except (AttributeError, OSError):
                pass
            time.sleep(0.02)
            os.write(1, payload)
            os._exit(0)
        print(json.dumps(result, allow_nan=False), flush=True)



if __name__ == '__main__':
    main()
