import argparse
from pathlib import Path

from pool_common import audit_pair, json_write, load_instance, read_artifact, verify_snapshot, within_pool


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    output = within_pool(arguments.output)
    report = {"admissible": False, "valid": False, "score": 0.}
    try:
        verify_snapshot()
        instance = load_instance(within_pool(arguments.instance) / "input")
        kernels, digest = read_artifact(arguments.artifact, instance["config"], with_digest=True)
        report = audit_pair(kernels, instance)
        report["artifact_sha256"] = digest
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    json_write(output, report)
    print({key: report.get(key) for key in ("admissible", "valid", "score", "error")}, flush=True)


if __name__ == "__main__":
    main()
