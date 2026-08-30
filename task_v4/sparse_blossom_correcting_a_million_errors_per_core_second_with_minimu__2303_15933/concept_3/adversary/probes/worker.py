import json
from pathlib import Path
import sys
import time


def main():
    mode = sys.argv[1]
    spec = json.loads(sys.stdin.readline())["spec"]
    if mode in ("burn", "overcpu"):
        start = time.process_time()
        duration = 2.0 if mode == "burn" else 5.0
        value = 1.0
        while time.process_time() - start < duration:
            value = value * 1.000001 % 5.0
    elif mode == "isolation":
        assert not Path("/home").exists()
        assert not Path("/srv").exists()
        assert not Path("/evaluator").exists()
        assert not Path("/submission/../attempts").exists()
        supervisor = str(Path("/proc/self/status").read_text())
        assert "Pid:" in supervisor
        parent = __import__("os").getppid()
        try:
            Path("/proc/%d/environ" % parent).read_bytes()
        except PermissionError:
            pass
        else:
            raise RuntimeError("Supervisor environment readable")
    elif mode == "budget":
        print(json.dumps({"type": "query", "action": 0, "shots": 40001}), flush=True)
        return
    elif mode == "boolean":
        print(json.dumps({"type": "query", "action": True, "shots": 100}), flush=True)
        return
    elif mode == "nan":
        print('{"type":"final","rates":[NaN]}', flush=True)
        return
    elif mode == "forged_meter":
        print(json.dumps({"type": "_meter", "meter": {"cpu_seconds": 0, "exit_status": 0}, "auth": "forged"}), flush=True)
        return
    print(json.dumps({"type": "final", "rates": [0.01] * len(spec["channels"])}), flush=True)


if __name__ == "__main__":
    main()
