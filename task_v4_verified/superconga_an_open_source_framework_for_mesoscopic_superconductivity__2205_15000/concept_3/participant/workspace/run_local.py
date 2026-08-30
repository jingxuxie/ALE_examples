import argparse
import json
import os
from pathlib import Path
import resource
import selectors
import subprocess
import sys
import tempfile
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

import bdg

PARTICIPANT = Path(__file__).resolve().parents[1]
TARGET = json.loads((PARTICIPANT / "input" / "target.json").read_text())


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (90, 95))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))


def metrics(truth, estimate):
    true_sites = {item["site"] for item in truth["impurities"]}
    predicted_sites = {item["site"] for item in estimate["impurities"]}
    support_f1 = 2 * len(true_sites & predicted_sites) / (len(true_sites) + len(predicted_sites))
    strength_error = float(np.linalg.norm(bdg.potential_of(estimate) - bdg.potential_of(truth)) / np.linalg.norm(bdg.potential_of(truth)))
    vortex_exact = sorted(estimate["vortices"]) == sorted(truth["vortices"])
    return {"support_f1": support_f1, "relative_strength_error": strength_error, "vortex_exact": int(vortex_exact),
            "joint_success": int(support_f1 >= TARGET["episode"]["support_f1_min"]
                                 and strength_error <= TARGET["episode"]["relative_strength_error_max"] and vortex_exact)}


def local_episode(case, entry):
    table = bdg.ldos_table(case["scene"])
    result = {"id": case["id"], "family": case["family"], "protocol_valid": False, "queries": 0}
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PARTICIPANT / "workspace") + os.pathsep + str(PARTICIPANT)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ldos-local-") as scratch:
        process = subprocess.Popen([sys.executable, str(entry)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, cwd=scratch, env=environment,
                                   preexec_fn=limits, start_new_session=True)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        buffer = b""
        errors = b""
        final = None
        deadline = start + bdg.SPEC["wall_seconds"]
        stdout_open = True
        os.set_blocking(process.stdin.fileno(), False)

        def send(message):
            payload = (json.dumps(message, allow_nan=False) + "\n").encode("utf-8")
            while payload:
                if time.monotonic() >= deadline:
                    raise ValueError("wall timeout sending observation")
                try:
                    written = os.write(process.stdin.fileno(), payload)
                    payload = payload[written:]
                except BlockingIOError:
                    time.sleep(0.005)

        try:
            send({"type": "metadata", "protocol": "ldos-jsonl-v1", "model": bdg.SPEC, "target": TARGET})
            while selector.get_map() or process.poll() is None:
                if time.monotonic() >= deadline:
                    raise ValueError("wall timeout")
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        if key.data == "stdout":
                            stdout_open = False
                        continue
                    if key.data == "stderr":
                        errors += chunk
                        if len(errors) > 65536:
                            raise ValueError("stderr limit")
                        continue
                    if final is not None:
                        raise ValueError("output after final")
                    buffer += chunk
                    if len(buffer.split(b"\n", 1)[0]) > 65536:
                        raise ValueError("stdout line limit")
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if len(line) > 65536 or final is not None:
                            raise ValueError("invalid extra output")
                        message = parse_message(line)
                        if message.get("type") == "final":
                            if set(message) != {"type", "estimate"}:
                                raise ValueError("invalid final keys")
                            final = bdg.validate_scene(message["estimate"])
                            if buffer:
                                raise ValueError("output after final")
                            process.stdin.close()
                            deadline = min(deadline, time.monotonic() + 3)
                            continue
                        site, energy_index = bdg.validate_action(message)
                        if result["queries"] >= bdg.SPEC["query_budget"]:
                            raise ValueError("query limit")
                        result["queries"] += 1
                        send({"type": "observation", "query_index": result["queries"], "site": site,
                              "energy_index": energy_index, "value": round(float(table[site, energy_index]), 12),
                              "remaining": bdg.SPEC["query_budget"] - result["queries"]})
                if not stdout_open and final is None:
                    raise ValueError("EOF before final")
            if process.returncode != 0 or final is None:
                raise ValueError("failed process")
            result.update({"protocol_valid": True, "estimate": final, "metrics": metrics(case["scene"], final)})
        except (ValueError, TypeError, OSError) as error:
            result["error"] = str(error)
            result["metrics"] = {"support_f1": 0.0, "relative_strength_error": 2.0, "vortex_exact": 0, "joint_success": 0}
        finally:
            if process.poll() is None:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            selector.close()
            for stream in (process.stdin, process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()
        result["stderr"] = errors.decode("utf-8", errors="replace")
    result["wall_seconds"] = time.monotonic() - start
    return result


def parse_message(line):
    def pairs(items):
        message = {}
        for key, value in items:
            if key in message:
                raise ValueError("duplicate JSON key")
            message[key] = value
        return message

    def constant(value):
        raise ValueError("nonfinite JSON")

    message = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(message, dict):
        raise ValueError("message must be object")
    return message


def main():
    parser = argparse.ArgumentParser(description="Public labeled JSONL practice; not a security sandbox.")
    parser.add_argument("--submission", type=Path, default=PARTICIPANT / "baseline")
    parser.add_argument("--entry", default="solve.py")
    parser.add_argument("--split", choices=("train", "calibration"), default="train")
    parser.add_argument("--case", type=int)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    entry = (arguments.submission / arguments.entry).resolve()
    if not entry.is_file():
        parser.error("submission entry not found")
    cases = json.loads((PARTICIPANT / "input" / (arguments.split + ".json")).read_text())["episodes"]
    if arguments.case is not None:
        if not 0 <= arguments.case < len(cases):
            parser.error("case out of range")
        cases = [cases[arguments.case]]
    results = []
    for case in cases:
        result = local_episode(case, entry)
        results.append(result)
        print(json.dumps(result, allow_nan=False), flush=True)
    summary = {"joint_success": float(np.mean([result["metrics"]["joint_success"] for result in results])),
               "protocol_failures": sum(not result["protocol_valid"] for result in results), "official_result": False}
    print(json.dumps(summary, allow_nan=False))
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps({"summary": summary, "episodes": results}, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
