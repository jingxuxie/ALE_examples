import ctypes
import json
import math
import os
import resource
import sys


def main():
    if ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError("cannot protect the resource supervisor")
    candidate = os.fork()
    if candidate == 0:
        try:
            os.setsid()
            for descriptor, path in [(1, "/work/solution.stdout"), (2, "/work/solution.stderr")]:
                opened = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
                os.dup2(opened, descriptor)
                if opened != descriptor:
                    os.close(opened)
            os.closerange(3, 1024)
            budget = math.ceil(float(sys.argv[2]))
            resource.setrlimit(resource.RLIMIT_CPU, (budget, budget + 1))
            resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
            os.execv("/usr/bin/python3", ["/usr/bin/python3", "/submission/" + sys.argv[1],
                                       "/work/input.json", "/work/output.json"])
        except BaseException as error:
            os.write(2, (type(error).__name__ + ": " + str(error)).encode())
            os._exit(126)
    waited, status, usage = os.wait4(candidate, 0)
    if waited != candidate:
        raise RuntimeError("resource supervisor waited on the wrong process")
    print(json.dumps({"cpu_seconds": usage.ru_utime + usage.ru_stime,
                      "user_cpu_seconds": usage.ru_utime, "system_cpu_seconds": usage.ru_stime,
                      "max_rss_kib": usage.ru_maxrss, "returncode": os.waitstatus_to_exitcode(status)}), flush=True)


if __name__ == "__main__":
    main()
