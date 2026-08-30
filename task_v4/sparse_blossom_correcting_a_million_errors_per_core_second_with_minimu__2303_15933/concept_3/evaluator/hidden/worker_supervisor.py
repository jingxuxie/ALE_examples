import ctypes
import hashlib
import hmac
import json
import os
import resource
import signal
import subprocess
import sys
import time


def main():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(4, 0, 0, 0, 0) != 0 or libc.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError("Supervisor protection unavailable")
    control = bytearray()
    while not control.endswith(b"\n"):
        chunk = os.read(0, 1)
        if not chunk or len(control) > 4096:
            raise RuntimeError("Invalid supervisor control")
        control.extend(chunk)
    settings = json.loads(control)
    key = bytes.fromhex(settings["key"])
    cpu_limit = int(settings["cpu_limit"])

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))

    child = subprocess.Popen(sys.argv[1:], preexec_fn=limits, close_fds=True)
    payload = {"type": "_ready"}
    payload["auth"] = hmac.new(key, b"ready", hashlib.sha256).hexdigest()
    print(json.dumps(payload), flush=True)
    usage_total = 0.0
    exit_status = None
    while True:
        try:
            process_id, status, usage = os.wait4(-1, 0)
        except ChildProcessError:
            break
        usage_total += usage.ru_utime + usage.ru_stime
        if process_id == child.pid:
            exit_status = os.waitstatus_to_exitcode(status)
            for name in os.listdir("/proc"):
                if name.isdigit() and int(name) not in (1, os.getpid()):
                    try:
                        os.kill(int(name), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
    meter = {"cpu_seconds": usage_total, "exit_status": exit_status}
    encoded = json.dumps(meter, sort_keys=True, separators=(",", ":"))
    print(json.dumps({"type": "_meter", "meter": meter,
                      "auth": hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()}), flush=True)


if __name__ == "__main__":
    main()
