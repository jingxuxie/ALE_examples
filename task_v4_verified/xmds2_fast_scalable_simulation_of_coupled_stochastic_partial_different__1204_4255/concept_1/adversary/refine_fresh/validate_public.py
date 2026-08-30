import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from model import check


def main():
    examples = [json.loads(line) for line in (ROOT / "participant" / "input" / "examples.jsonl").read_text().splitlines() if line.strip()]
    instances = [item.get("instance", item) for item in examples]
    available = os.sched_getaffinity(0)
    cpu = 198 if 198 in available else min(available)

    def limits():
        os.sched_setaffinity(0, {cpu})
        resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_CPU, (120, 121))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.monotonic()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", TMPDIR=str(HERE / "tmp"))
    process = subprocess.Popen([sys.executable, str(HERE / "candidate" / "solve.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=HERE, env=environment, preexec_fn=limits, start_new_session=True)
    try:
        output, errors = process.communicate("".join(json.dumps(instance) + "\n" for instance in instances), timeout=120)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    elapsed = time.monotonic() - started
    assert process.returncode == 0, errors
    answers = [json.loads(line) for line in output.splitlines()]
    assert len(answers) == len(instances)
    checked = [check(instance, answer) for instance, answer in zip(instances, answers)]
    (HERE / "public_answers.jsonl").write_text(output)
    report = {"count": len(instances), "valid_count": len(checked), "elapsed_seconds": elapsed, "cpu_affinity": [cpu], "checks": checked, "stderr": errors}
    (HERE / "public_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "checks"}))


if __name__ == "__main__":
    main()
