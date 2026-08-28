import os
from pathlib import Path
import sys

os.environ["SPIN_SECONDS"]="95"
os.environ["SPIN_NODES"]="3"
os.environ["SPIN_SAVE_BLOCKS"]="1"
entry=Path(__file__).with_name("frozen_solve.py")
os.execv(sys.executable,[sys.executable,str(entry),*sys.argv[1:]])
