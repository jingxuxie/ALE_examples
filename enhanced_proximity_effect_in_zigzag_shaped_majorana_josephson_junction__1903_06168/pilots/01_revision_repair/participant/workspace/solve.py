from pathlib import Path
import sys

sys.dont_write_bytecode = True

from protocol import main


if __name__ == '__main__':
    main(Path(__file__).resolve().parent / 'upstream/zigzag.py')
