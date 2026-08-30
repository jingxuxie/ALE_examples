import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("trusted_certificate_checker", ROOT / "hidden" / "checker.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    certificate = arguments.submission / "certificate.json" if arguments.submission.is_dir() else arguments.submission
    report = CHECKER.verify(ROOT / "hidden" / "instances.json", certificate)
    payload = json.dumps(report, indent=2, allow_nan=False)
    if arguments.report:
        arguments.report.write_text(payload + "\n")
    print(payload)


if __name__ == "__main__":
    main()
