import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from sandbox import sandbox_command


def main():
    canary = str(ROOT / "evaluator/hidden/isolation_canary.txt")
    payload = """
import json, os, resource, socket
from pathlib import Path
results = {}
for name, operation in [
    ('hidden_read', lambda: Path(CANARY).read_text()),
    ('parent_enumeration', lambda: os.listdir(str(Path(CANARY).parents[2]))),
    ('network_socket', lambda: socket.socket()),
    ('child_process', lambda: os.fork()),
    ('proc_environment', lambda: Path('/proc/self/environ').read_bytes()),
]:
    try:
        operation()
        results[name] = False
    except OSError:
        results[name] = True
results['cpu_limit'] = resource.getrlimit(resource.RLIMIT_CPU)[0]
results['memory_limit'] = resource.getrlimit(resource.RLIMIT_AS)[0]
import numpy as np
results['numpy_works'] = float(np.linalg.det(np.eye(3))) == 1.0
print(json.dumps(results))
""".replace("CANARY", repr(canary))
    with tempfile.TemporaryDirectory(prefix="of-isolation-check-") as temporary:
        command, environment = sandbox_command(["/usr/bin/python3", "-c", payload], {}, ROOT / "participant", ROOT / "participant/baseline", Path(temporary), cpu_seconds=10, memory_mb=2048)
        process = subprocess.run(command, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, close_fds=True)
    if process.returncode:
        raise RuntimeError(process.stderr.decode())
    report = json.loads(process.stdout)
    assert all(report[name] for name in ["hidden_read", "parent_enumeration", "network_socket", "child_process", "proc_environment", "numpy_works"])
    report["valid"] = True
    (ROOT / "adversary/isolation_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
