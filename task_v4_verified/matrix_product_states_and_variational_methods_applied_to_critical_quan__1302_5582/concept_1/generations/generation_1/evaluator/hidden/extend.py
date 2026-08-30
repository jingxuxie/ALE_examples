"""Produce private, uncalibrated same-physics ratchet proposals, not new trivia."""

import argparse
import json
from pathlib import Path

from suite import extension_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    proposals = [{"family": family, "request": request} for family, request in extension_cases(args.seed, args.count)]
    Path(args.output).write_text(json.dumps({"status": "uncalibrated proposals only", "cases": proposals}, indent=2))


if __name__ == "__main__":
    main()
