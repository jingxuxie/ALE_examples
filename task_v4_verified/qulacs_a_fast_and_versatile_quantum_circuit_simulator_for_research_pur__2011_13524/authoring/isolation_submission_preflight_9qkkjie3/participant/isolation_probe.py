import errno
import json
import os
from pathlib import Path
import socket
import sys


def denied(operation):
    try:
        operation()
    except OSError as error:
        return error.errno in {errno.ENOENT, errno.EACCES, errno.EPERM, errno.EROFS}
    return False


def read_file(path):
    with open(path, "rb") as stream:
        stream.read(1)


def open_without_reading(path):
    descriptor = os.open(path, os.O_RDONLY)
    os.close(descriptor)


def main():
    participant = Path(sys.argv[1])
    output = Path(sys.argv[2])
    manifest = json.loads((participant / "probe-input.json").read_text())
    checks = {"participant_read": (participant / "public.txt").read_text() == "PUBLIC_PREFLIGHT_ONLY\n"}
    checks["participant_write_denied"] = denied(lambda: (participant / "must-not-write").write_text("bad"))
    checks["participant_truncate_denied"] = denied(lambda: os.truncate(participant / "public.txt", 0))
    for path in manifest.get("forbidden_open_files", []):
        checks[f"open_denied:{path}"] = denied(lambda path=path: open_without_reading(path))
    for path in manifest["forbidden_files"]:
        checks[f"read_denied:{path}"] = denied(lambda path=path: read_file(path))
        checks[f"truncate_denied:{path}"] = denied(lambda path=path: os.truncate(path, 0))
    for path in manifest["forbidden_directories"]:
        checks[f"listing_denied:{path}"] = denied(lambda path=path: list(Path(path).iterdir()))
    linked = output / "escape-link"
    linked.symlink_to(manifest["forbidden_files"][0])
    checks["symlink_escape_denied"] = denied(lambda: read_file(linked))
    linked.unlink()
    (output / "write-check.txt").write_text("PUBLIC_OUTPUT_ONLY\n")
    checks["output_write"] = (output / "write-check.txt").read_text() == "PUBLIC_OUTPUT_ONLY\n"
    checks["outside_write_denied"] = denied(lambda: Path(manifest["forbidden_files"][0]).write_text("bad"))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.25)
            checks["host_loopback_denied"] = connection.connect_ex(("127.0.0.1", manifest["host_port"])) != 0
    except PermissionError:
        checks["host_loopback_denied"] = True
    for family in (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX, socket.AF_NETLINK):
        def create_socket(family=family):
            with socket.socket(family, socket.SOCK_DGRAM):
                pass
        checks[f"socket_family_denied:{family}"] = denied(create_socket)
    status = Path("/proc/self/status").read_text()
    checks["no_effective_capabilities"] = "CapEff:\t0000000000000000" in status
    checks["seccomp_enforced"] = "Seccomp:\t2" in status
    checks["no_new_privileges"] = "NoNewPrivs:\t1" in status
    result = {"scientific_attempt": False, "checks": checks, "passed": all(checks.values())}
    (output / "probe-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
