import json
import os
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

from engine import Policy
from active import ActivePolicy


def exchange(message):
    print(json.dumps(message, allow_nan=False, separators=(',', ':')), flush=True)
    line = sys.stdin.readline()
    if not line:
        raise RuntimeError('evaluator_closed')
    return json.loads(line)


def main():
    hello = json.loads(sys.stdin.readline())
    ActivePolicy(hello).run(exchange)


if __name__ == '__main__':
    main()
