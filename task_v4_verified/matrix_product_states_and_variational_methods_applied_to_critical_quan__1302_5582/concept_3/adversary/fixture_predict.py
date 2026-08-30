import argparse
import json
import os
from pathlib import Path
import socket
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    configuration = json.loads(Path(__file__).with_name("fixture.json").read_text())
    mode = configuration["mode"]
    output = Path(arguments.output)
    if mode == "raw":
        output.write_text(configuration["text"])
    elif mode == "sleep":
        time.sleep(20)
    elif mode == "cpu":
        while True:
            pass
    elif mode == "memory":
        allocation = bytearray(3 * 1024 ** 3)
        output.write_text(str(len(allocation)))
    elif mode == "oversized":
        output.write_bytes(b"x" * (2 * 1024 ** 2))
    elif mode == "symlink_output":
        output.symlink_to(arguments.train)
    elif mode == "probe":
        checks = {}
        for path in configuration["forbidden_reads"]:
            try:
                Path(path).read_bytes()
                checks["read:" + path] = False
            except OSError:
                checks["read:" + path] = True
        for path in (arguments.input, arguments.train, str(Path(__file__))):
            try:
                with open(path, "ab") as stream:
                    stream.write(b"tamper")
                checks["write:" + path] = False
            except OSError:
                checks["write:" + path] = True
        try:
            connection = socket.socket()
            connection.close()
            checks["network"] = False
        except OSError:
            checks["network"] = True
        try:
            child = os.fork()
            if child == 0:
                os._exit(0)
            os.waitpid(child, 0)
            checks["fork"] = False
        except OSError:
            checks["fork"] = True
        try:
            os.execv("/usr/bin/true", ["true"])
            checks["exec"] = False
        except OSError:
            checks["exec"] = True
        import numpy
        import scipy
        checks["numpy_scipy"] = numpy.__version__ == "1.21.5" and scipy.__version__ == "1.8.0"
        Path("/tmp/scratch").write_text("allowed")
        checks["scratch"] = Path("/tmp/scratch").read_text() == "allowed"
        output.write_text(json.dumps(checks, allow_nan=False))
    else:
        raise ValueError("Unknown fixture")


if __name__ == "__main__":
    main()
