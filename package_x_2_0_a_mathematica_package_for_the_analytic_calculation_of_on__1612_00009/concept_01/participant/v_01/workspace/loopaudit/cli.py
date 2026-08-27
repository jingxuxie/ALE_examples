import argparse
import json
from pathlib import Path

from .service import run_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="production")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    settings = json.loads((root / "profiles.json").read_text())[arguments.profile]
    result = run_cases(json.loads(Path(arguments.requests).read_text()), settings)
    Path(arguments.output).parent.mkdir(parents=True, exist_ok=True)
    Path(arguments.output).write_text(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
