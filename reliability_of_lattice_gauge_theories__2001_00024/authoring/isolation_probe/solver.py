import pathlib
import socket


def solve(case):
    checks = {name: pathlib.Path(path).exists() for name, path in case["forbidden"].items()}
    accessible = pathlib.Path(case["public_path"]).is_file()
    network_blocked = False
    connection = socket.socket()
    connection.settimeout(0.3)
    try:
        connection.connect(("1.1.1.1", 443))
    except OSError:
        network_blocked = True
    finally:
        connection.close()
    return {"forbidden_visible": checks, "public_accessible": accessible, "network_blocked": network_blocked}
