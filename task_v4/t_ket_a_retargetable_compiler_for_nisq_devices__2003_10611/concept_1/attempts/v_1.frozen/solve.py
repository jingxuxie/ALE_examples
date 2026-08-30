import time

STARTED = time.monotonic()

import json
import ctypes
import os
from pathlib import Path
import sys


def main():
    started = STARTED
    budget = min(5.5, max(0.01, float(os.environ.get("ROUTE_TIME", "4.0"))))
    instance = json.load(sys.stdin)
    directory = Path(os.path.abspath(__file__)).parent
    library_path = directory / "router.so"
    def build():
        import subprocess
        temporary = directory / (".router." + str(os.getpid()) + ".so")
        try:
            subprocess.run(
                ["g++", "-O3", "-std=c++17", "-shared", "-fPIC",
                 str(directory / "router.cpp"), "-o", str(temporary)],
                check=True,
                stdout=sys.stderr,
            )
            os.replace(temporary, library_path)
        finally:
            temporary.unlink(missing_ok=True)

    if not library_path.exists():
        build()
    fields = [str(instance["n"]), str(len(instance["gates"])), str(len(instance["edges"]))]
    fields.extend(map(str, instance["initial"]))
    for edge in instance["edges"]:
        fields.extend(map(str, edge))
    for gate in instance["gates"]:
        fields.extend(map(str, gate))
    payload = " ".join(fields).encode()
    try:
        library = ctypes.CDLL(str(library_path))
    except OSError:
        build()
        library = ctypes.CDLL(str(library_path))
    route = library.route_instance
    route.argtypes = [ctypes.c_char_p, ctypes.c_double, ctypes.c_double]
    route.restype = ctypes.c_char_p
    answer = route(payload, budget, started + budget)
    if not answer:
        raise RuntimeError("Native routing failed")
    sys.stdout.buffer.write(answer)


if __name__ == "__main__":
    main()
