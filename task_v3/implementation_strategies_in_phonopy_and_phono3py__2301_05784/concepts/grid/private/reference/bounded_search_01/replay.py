"""Replay only the existing search manifest through the shared isolated runner."""

import argparse
from pathlib import Path

from run import CONCEPT, MANIFEST, REFERENCE, load_evaluator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append", dest="case_ids")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(REFERENCE) or output.exists():
        raise SystemExit("Choose a new report path under concepts/grid/private/reference")
    evaluator = load_evaluator()
    evaluator.load_shared().evaluate(
        CONCEPT, CONCEPT / "attempt/solve.py", split="search", output=output,
        score_case=evaluator.score_case, case_ids=args.case_ids, manifest_path=MANIFEST,
    )


if __name__ == "__main__":
    main()
