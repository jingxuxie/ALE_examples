import argparse
import json
import math
import os
from pathlib import Path
import resource
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--burn", type=float, default=0.0)
    parser.add_argument("--memory", action="store_true")
    arguments = parser.parse_args()
    spec = json.loads(input())["spec"]
    assert not Path("/srv/home/xuandong/mnt/jingxu/ALE").exists()
    assert not Path("/home/ALE").exists()
    assert not Path("/evaluator").exists()
    assert not Path("/participant/evaluator").exists()
    assert resource.getrlimit(resource.RLIMIT_AS) == (3 * 1024**3, 3 * 1024**3)
    try:
        Path("/participant/write_probe").write_text("not permitted")
    except OSError:
        pass
    else:
        raise AssertionError("participant is writable")
    assert Path("/submission").is_dir()
    Path("/submission/audit_scratch.json").write_text(json.dumps({"writable": True}))
    if arguments.memory:
        try:
            allocation = bytearray(4 * 1024**3)
        except MemoryError:
            pass
        else:
            raise AssertionError("address space cap not enforced")
    start = time.process_time()
    while time.process_time() - start < arguments.burn:
        math.sqrt(1.2345)
    rates = [math.sqrt(channel["rate_bounds"][0] * channel["rate_bounds"][1]) for channel in spec["channels"]]
    print(json.dumps({"type": "final", "rates": rates}), flush=True)


if __name__ == "__main__":
    main()
