import argparse
import json
from pathlib import Path
import tempfile

from model import Episode, FAMILIES, SHAPES
from transport import aggregate, launch_command, run_episode, snapshot_submission


def main():
    parser = argparse.ArgumentParser(description="Public development episodes, never the hidden benchmark.")
    parser.add_argument("--submission", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--policy", default="baseline/policy.py")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--family", choices=FAMILIES + ("all",), default="all")
    parser.add_argument("--shape", choices=("4x4", "4x5", "5x5", "all"), default="4x4")
    parser.add_argument("--isolation", choices=("audit", "bwrap"), default="audit")
    parser.add_argument("--report")
    arguments = parser.parse_args()
    families = FAMILIES if arguments.family == "all" else (arguments.family,)
    shapes = SHAPES if arguments.shape == "all" else (tuple(map(int, arguments.shape.split("x"))),)
    records = []
    with tempfile.TemporaryDirectory(prefix="mrb-public-") as directory:
        directory = Path(directory)
        snapshot = directory / "submission"
        artifact_hash = snapshot_submission(arguments.submission, snapshot, arguments.policy)
        command = launch_command(snapshot, arguments.policy, arguments.isolation)
        for family_index, family in enumerate(families):
            for shape_index, shape in enumerate(shapes):
                seed = arguments.seed + 1009 * FAMILIES.index(family) + 53 * SHAPES.index(shape)
                episode = Episode(seed, family, shape)
                record = run_episode(episode, command, snapshot, directory / "stderr.txt", isolation=arguments.isolation)
                record.update(family=family, qubits=episode.grid.qubits, public_seed=seed)
                records.append(record)
        report = aggregate(records, isolated=False)
        report.update(development_only=True, isolation=arguments.isolation, submission_sha256=artifact_hash)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
