import json
import math
import os
import selectors
import subprocess
import time

import numpy as np

from pair_model import initial_observation


def run_policy(command, models, tables, wall_seconds=180, environment=None, preexec_fn=None):
    start = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env=environment, preexec_fn=preexec_fn,
                               bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    buffer = bytearray()
    records = []

    def send(message):
        process.stdin.write((json.dumps(message, allow_nan=False) + "\n").encode())
        process.stdin.flush()

    def receive():
        while b"\n" not in buffer:
            remaining = wall_seconds - (time.monotonic() - start)
            if remaining <= 0 or not selector.select(max(0, remaining)):
                raise TimeoutError("policy wall-time limit")
            block = os.read(process.stdout.fileno(), 65536)
            if not block:
                raise RuntimeError("policy exited before final estimate")
            buffer.extend(block)
            if len(buffer) > 1048576:
                raise ValueError("policy message exceeds 1 MiB")
        line, _, rest = buffer.partition(b"\n")
        buffer[:] = rest
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("policy messages must be objects")
        return value

    try:
        for index, (model, table) in enumerate(zip(models, tables)):
            remaining = 160
            observed = set(mask for mask in range(256) if mask.bit_count() <= 2)
            query_count = 0
            send(initial_observation(model, table, remaining))
            for action_index in range(200):
                action = receive()
                if set(action) == {"estimate"}:
                    estimate = action["estimate"]
                    if isinstance(estimate, bool) or not isinstance(estimate, (float, int)) or not math.isfinite(estimate):
                        raise ValueError("estimate must be a finite number")
                    records.append({"index": index, "family": model["family"],
                                    "estimate": float(estimate), "truth": float(table[-1]),
                                    "error": float(estimate - table[-1]),
                                    "cost": 160 - remaining, "queries": query_count})
                    send({"event": "accepted"})
                    break
                if set(action) != {"query"} or not isinstance(action["query"], list) or not 1 <= len(action["query"]) <= 160:
                    raise ValueError("expected query list or estimate")
                requested = action["query"]
                if any(isinstance(mask, bool) or not isinstance(mask, int) or not 0 <= mask < 256 for mask in requested):
                    raise ValueError("query masks must be integers in [0,255]")
                if len(set(requested)) != len(requested):
                    raise ValueError("duplicate mask in query batch")
                price = 0
                for mask in requested:
                    order = mask.bit_count()
                    if order > 6:
                        raise ValueError("at most six virtual orbitals per CAS experiment")
                    if mask not in observed:
                        price += {3: 1, 4: 4, 5: 16, 6: 64}.get(order, 0)
                if price > remaining:
                    raise ValueError("CAS experiment budget exceeded")
                remaining -= price
                query_count += sum(mask not in observed for mask in requested)
                observed.update(requested)
                send({"event": "result", "remaining": remaining,
                      "values": [[mask, float(table[mask])] for mask in requested]})
            else:
                raise ValueError("too many actions without an estimate")
        send({"event": "done"})
        process.stdin.close()
        process.wait(timeout=max(0.1, wall_seconds - (time.monotonic() - start)))
        if process.returncode != 0:
            raise RuntimeError("policy failed on termination")
        return records, time.monotonic() - start
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()


def summarize(records, elapsed, valid=True, reason="evaluated"):
    if not valid or not records:
        return {"core_score": 0.0, "worst_family_score": 0.0,
                "resource_score": 0.0, "runtime_seconds": elapsed,
                "passed": False, "valid": valid, "reason": reason, "records": records}
    errors = np.asarray([record["error"] for record in records])
    family_rmse = {family: float(np.sqrt(np.mean([record["error"] ** 2 for record in records if record["family"] == family])))
                   for family in sorted({record["family"] for record in records})}
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    worst = max(family_rmse.values())
    passed = rmse <= 1.0e-5 and worst <= 2.5e-5
    return {"core_score": max(0.0, 1.0 - rmse / 1.0e-4),
            "worst_family_score": max(0.0, 1.0 - worst / 2.5e-4),
            "rmse_hartree": rmse, "worst_family_rmse_hartree": worst,
            "family_rmse_hartree": family_rmse,
            "maximum_absolute_error_hartree": float(np.max(np.abs(errors))),
            "resource_score": 1.0 - sum(record["cost"] for record in records) / (320 * len(records)),
            "maximum_query_cost": max(record["cost"] for record in records),
            "runtime_seconds": elapsed, "passed": passed, "valid": True,
            "reason": "accuracy and budget targets met" if passed else "energy accuracy target missed",
            "records": records}
