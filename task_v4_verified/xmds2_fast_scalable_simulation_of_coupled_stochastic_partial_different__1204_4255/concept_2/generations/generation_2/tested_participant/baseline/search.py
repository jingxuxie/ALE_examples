import argparse
import hashlib
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    started = time.monotonic()
    content = Path(__file__).with_name("champion.json").read_bytes()
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    print(json.dumps({"submission": str(destination), "source": "verified_generation_1_champion", "sha256": hashlib.sha256(content).hexdigest(), "runtime_seconds": time.monotonic() - started}))


if __name__ == "__main__":
    main()
