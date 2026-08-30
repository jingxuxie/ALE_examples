import argparse
import json
import signal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "hidden"))
from checker import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    def timed_out(signum, frame):
        raise TimeoutError("60-second evaluation limit exceeded")
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(60)
    try:
        result = evaluate(args.submission)
    except TimeoutError as error:
        result = {"core_score": 0, "worst_family_score": 0, "resource_score": 0,
                  "runtime_seconds": 60, "valid": False, "passed": False, "reason": str(error)}
    signal.alarm(0)
    text = json.dumps(result, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
