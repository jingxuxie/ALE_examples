import json
from pathlib import Path
import time


SIDE = Path(__file__).resolve().parent


def main():
    deadline = time.monotonic() + 900
    with (SIDE / "cpu_clocks.jsonl").open("w") as output:
        while time.monotonic() < deadline:
            for name in ["official_replay", "relaxed_diagnostic"]:
                path = SIDE / (name + "_processes.jsonl")
                try:
                    with path.open("rb") as source:
                        source.seek(0, 2)
                        source.seek(max(0, source.tell() - 32768))
                        row = json.loads(source.read().splitlines()[-1])
                except (OSError, ValueError, IndexError):
                    continue
                for process in row["processes"]:
                    if not process["command"].startswith("/usr/bin/python3 -I"):
                        continue
                    pid = process["pid"]
                    clocks = {}
                    for name_clock, which in [("prof", 0), ("virt", 1), ("sched", 2)]:
                        try:
                            clocks[name_clock] = time.clock_gettime((~pid << 3) | which)
                        except OSError:
                            clocks[name_clock] = None
                    output.write(json.dumps(dict(run=name, pid=pid, observed_unix=time.time(),
                        process_clocks_seconds=clocks, proc_cpu_seconds=process["proc_cpu_seconds"],
                        proc_cpu_limit=process["cpu_limit"])) + "\n")
                    output.flush()
            if (SIDE / "relaxed_diagnostic_launcher.json").exists():
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
