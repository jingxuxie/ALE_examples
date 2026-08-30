import json
import os
from pathlib import Path
import resource
import socket
import sys


def main():
    package = Path(sys.argv[1])
    output = Path(sys.argv[2])
    tests = {}
    protected = {
        "private_challenge": package / "concept_1/generations/generation_2/evaluator/hidden/manifest.json",
        "private_witness": package / "concept_2/adversary/search_run/witness.json",
        "hidden_material": package / "concept_3/evaluator/hidden/model.npz",
        "previous_submission": package / "concept_1/attempts/v_2/solve.py",
        "paper_source": package / "authoring/sources/paper.html",
        "credentials_config": Path("/home/xuandong/.codex/config.toml"),
        "procfs": Path("/proc/self/environ"),
    }
    for name, path in protected.items():
        try:
            path.read_bytes()
            tests[name + "_denied"] = False
        except PermissionError:
            tests[name + "_denied"] = True
    try:
        (Path(__file__).parent / "forbidden_write.txt").write_text("not allowed")
        tests["participant_write_denied"] = False
    except PermissionError:
        tests["participant_write_denied"] = True
    try:
        socket.socket()
        tests["network_socket_denied"] = False
    except PermissionError:
        tests["network_socket_denied"] = True
    first, second = socket.socketpair()
    first.close()
    second.close()
    tests["local_unnamed_ipc_works"] = True
    path = output / "write_test.txt"
    path.write_text("allowed")
    tests["output_read_write_works"] = path.read_text() == "allowed"
    import numpy as np
    tests["numerical_computation_works"] = bool(np.linalg.norm(np.eye(4)) == 2)
    result = {"valid": all(tests.values()), "tests": tests,
              "cpu_affinity_count": len(os.sched_getaffinity(0)),
              "address_space_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[1],
              "transport": "Landlock ABI1 plus seccomp; not a mount namespace",
              "scope": "Read/write content isolation and runtime checks; does not claim kernel-level metadata invisibility."}
    (output / "results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
