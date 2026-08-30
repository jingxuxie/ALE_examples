import json
import os
from pathlib import Path
import sys
import time


def main():
    parent = int(sys.argv[1])
    root = Path(__file__).resolve().parents[2]
    expected = str(root.relative_to(Path.cwd())) + "/evaluator/hidden/build_data.py"
    parent_command = Path(f"/proc/{parent}/cmdline").read_bytes().decode().replace("\0", " ")
    if expected not in parent_command:
        raise RuntimeError("Not the authorized new-generation builder")
    placements = {}
    while Path(f"/proc/{parent}/cmdline").exists():
        children_path = Path(f"/proc/{parent}/task/{parent}/children")
        try:
            children = [int(value) for value in children_path.read_text().split()]
        except FileNotFoundError:
            break
        for index, child in enumerate(children):
            cpu = 204 + index if index < 16 else 292 + index
            try:
                command = Path(f"/proc/{child}/cmdline").read_bytes().decode().replace("\0", " ")
                if expected not in command:
                    continue
                os.sched_setaffinity(child, {cpu})
            except ProcessLookupError:
                continue
            placements[str(child)] = cpu
        (root / "evaluator/hidden/worker_placement.json").write_text(json.dumps(placements, indent=2) + "\n")
        time.sleep(5)


if __name__ == "__main__":
    main()
