import csv
import os
from pathlib import Path
import socket
import sys


def main():
    training_path, query_path, output_path = sys.argv[1:]
    mode_path = Path(__file__).with_name("mode.txt")
    mode = mode_path.read_text().strip() if mode_path.exists() else "isolation"
    if mode == "isolation":
        participant = Path(os.environ["TASK_ROOT"])
        protected = [participant.parent / "evaluator" / "hidden" / "labels.json",
                     participant.parent / "evaluator" / "hidden" / "honeycomb_memory_stats.csv",
                     participant.parent.parent / "authoring" / "paper.pdf",
                     Path("/proc/self/environ"), Path(f"/proc/{os.getppid()}/environ")]
        for path in protected:
            try:
                with path.open("rb") as stream:
                    stream.read(1)
            except PermissionError:
                pass
            else:
                raise RuntimeError("protected file unexpectedly readable: " + str(path))
        for domain in [socket.AF_INET, socket.AF_UNIX]:
            try:
                connection = socket.socket(domain, socket.SOCK_STREAM)
            except PermissionError:
                pass
            else:
                connection.close()
                raise RuntimeError("socket unexpectedly permitted")
        with open(query_path, newline="") as stream:
            columns = csv.DictReader(stream).fieldnames
        if {"num_shots", "num_correct", "total_processing_seconds"}.intersection(columns):
            raise RuntimeError("outcome-dependent query metadata exposed")
    with open(query_path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    probability = "1e-15" if mode == "tiny" else "nan" if mode == "nan" else "0.5"
    with open(output_path, "w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["query_id", "p_failure"])
        for row in rows:
            writer.writerow([row["query_id"], probability])


if __name__ == "__main__":
    main()
