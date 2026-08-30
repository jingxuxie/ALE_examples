import json
from pathlib import Path
import sys

from routing import validate


if __name__ == "__main__":
    try:
        result = validate(json.loads(Path(sys.argv[1]).read_text()), json.loads(Path(sys.argv[2]).read_text()))
    except (ValueError, KeyError, TypeError, IndexError) as error:
        result = {"valid": False, "reason": str(error)}
    print(json.dumps(result))
