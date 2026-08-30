import json
import os
from pathlib import Path
import sys

import networkx
import numpy
import scipy.linalg

from contraction import baseline_plan


root = Path(__file__).resolve().parents[2]
assert not (root / "evaluator" / "hidden" / "challenge.json").exists()
assert not (root.parent / "concept_3" / "champions").exists()
assert (Path(os.environ["PARTICIPANT_DIR"]) / "input" / "examples.json").is_file()
assert len(os.sched_getaffinity(0)) == 1
scipy.linalg.svd(numpy.eye(4))
print(json.dumps(baseline_plan(json.load(sys.stdin))))
