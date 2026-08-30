import resource
import sys
from pathlib import Path


resource.setrlimit(resource.RLIMIT_CPU, (900, 901))
resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import json

from search_api import assess, parse_submission


try:
    parameters = parse_submission(sys.stdin.read(16385))
    result = assess(parameters, exhaustive="--exhaustive" in sys.argv[1:])
except (ValueError, OverflowError, FloatingPointError, RecursionError, MemoryError, ArithmeticError) as error:
    result = {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": "invalid_or_numerical_failure: " + str(error)[:200]}
print(json.dumps(result, allow_nan=False))
