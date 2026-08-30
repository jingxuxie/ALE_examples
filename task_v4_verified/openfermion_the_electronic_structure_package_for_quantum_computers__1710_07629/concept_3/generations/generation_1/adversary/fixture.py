"""Black-box malformed-output probe, copied into ephemeral test submissions."""

import json
import os
from pathlib import Path
import sys
import time


def main():
    mode = Path(__file__).with_name("mode.txt").read_text().strip()
    request = json.loads(Path(sys.argv[1]).read_text())
    output = Path(sys.argv[2])
    count = request["n_instances"]
    payload = {"schema_version": 1, "predictions": [[0.0, 0.0] for _ in range(count)]}
    if mode == "wrong_count":
        payload["predictions"].pop()
    elif mode == "wrong_shape":
        payload["predictions"][0] = [0.0]
    elif mode == "boolean":
        payload["predictions"][0][0] = True
    elif mode == "string":
        payload["predictions"][0][0] = "0.0"
    elif mode == "nan":
        payload["predictions"][0][0] = float("nan")
    elif mode == "infinity":
        payload["predictions"][0][0] = float("inf")
    elif mode == "extra_key":
        payload["extra"] = 4
    elif mode == "missing":
        return
    elif mode == "truncated":
        output.write_text('{"schema_version":1,"predictions":[')
        return
    elif mode == "duplicate_key":
        output.write_text(json.dumps(payload)[:-1] + ',"schema_version":1}')
        return
    elif mode == "oversized":
        output.write_text(" " * 200000)
        return
    elif mode == "symlink":
        destination = output.with_name("other.json")
        destination.write_text(json.dumps(payload))
        output.symlink_to(destination)
        return
    elif mode == "timeout":
        time.sleep(120)
        return
    elif mode == "flood":
        while True:
            os.write(1, b"X" * 65536)
    elif mode == "memory":
        bytearray(3 * 1024 ** 3)
        return
    elif mode == "public_inputs_only":
        import numpy as np
        with np.load(request["inputs"], allow_pickle=False) as archive:
            assert set(archive.files) == {"hopping", "interaction", "potential", "n_sites", "family"}
            assert len(archive["family"]) == count
        roots = [Path(__file__).resolve().parents[2] / "evaluator/hidden/test.npz",
                 Path(request["inputs"]).parents[2] / "hidden/test.npz",
                 Path("/proc/self/environ"), Path("/proc/self/mem")]
        for root in roots:
            try:
                root.read_bytes()
            except OSError:
                pass
            else:
                raise AssertionError("private read succeeded")
    output.write_text(json.dumps(payload) + "\n")


if __name__ == "__main__":
    main()
