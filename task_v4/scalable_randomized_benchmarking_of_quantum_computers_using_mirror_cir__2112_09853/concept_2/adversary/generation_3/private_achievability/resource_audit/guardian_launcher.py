import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--audit-path", required=True)
    arguments = parser.parse_args()
    audit_read, audit_write = os.pipe2(os.O_CLOEXEC)
    command = ["/usr/bin/bwrap", "--as-pid-1", "--die-with-parent", "--new-session", "--unshare-all", "--ro-bind", "/usr", "/usr"]
    for directory in ("/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command.extend(["--ro-bind", directory, directory])
    command.extend(["--dir", "/etc"])
    for filename in ("/etc/ld.so.cache", "/etc/localtime", "/etc/alternatives"):
        if Path(filename).exists():
            command.extend(["--ro-bind", filename, filename])
    command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", arguments.artifact, "/submission",
                    "--ro-bind", str(Path(__file__).with_name("guardian.py")), "/trusted/guardian.py",
                    "--chdir", "/submission", "--", sys.executable,
                    "-I", "-S", "-B", "/trusted/guardian.py", str(audit_write),
                    sys.executable, "-E", "-s", "-B", "-u", "/submission/policy.py"])
    process = subprocess.Popen(command, pass_fds=(audit_write,), close_fds=True)
    os.close(audit_write)
    received = bytearray()
    while True:
        data = os.read(audit_read, 4096)
        if not data:
            break
        received.extend(data)
        if len(received) > 4096:
            raise RuntimeError("oversized_guardian_audit")
    os.close(audit_read)
    result = process.wait()
    record = json.loads(received.decode())
    record["guardian_exit_code"] = result
    Path(arguments.audit_path).write_text(json.dumps(record, indent=2) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
