from pathlib import Path
import sys

sys.dont_write_bytecode = True
PILOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PILOT / 'participant/workspace'))

from protocol import main


if __name__ == '__main__':
    main(Path(__file__).resolve().parent / 'upstream/zigzag.py')
