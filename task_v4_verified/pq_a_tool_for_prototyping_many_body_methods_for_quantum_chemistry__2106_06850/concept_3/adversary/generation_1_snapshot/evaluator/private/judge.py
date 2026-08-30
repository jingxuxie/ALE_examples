"""Trusted worker; never mount this directory in a participant sandbox."""

import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (12, 13))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    private = Path(__file__).resolve().parent
    manifest = json.loads((private / "frozen_manifest.json").read_text(encoding="utf-8"))
    for name in ("engine.py", "targets.json"):
        digest = hashlib.sha256((private / name).read_bytes()).hexdigest()
        if digest != manifest["private_sha256"][name]:
            raise RuntimeError("frozen evaluator integrity check failed")
    specification = importlib.util.spec_from_file_location("trusted_fermion", private / "engine.py")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    print(json.dumps(module.evaluate_path(sys.argv[1], private / "targets.json"), allow_nan=False))


if __name__ == "__main__":
    main()
