from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
import sandbox_runner


def check_outer_timeout(stderr_kind):
    with tempfile.TemporaryDirectory(prefix="wall-classification-", dir="/tmp") as directory:
        scratch = Path(directory)
        process = SimpleNamespace(pid=12345, returncode=None)

        def fake_wait(timeout=None):
            if timeout is not None:
                raise sandbox_runner.subprocess.TimeoutExpired(["not-executed"], timeout)
            process.returncode = -9
            return process.returncode

        process.wait = fake_wait

        def fake_spawn(*args, **kwargs):
            stderr = scratch / "stderr.log"
            if stderr_kind == "missing":
                stderr.unlink()
            elif stderr_kind == "symlink":
                stderr.unlink()
                stderr.symlink_to(scratch / "absent")
            return process

        with patch.object(sandbox_runner, "sandbox_command", return_value=["not-executed"]), \
                patch.object(sandbox_runner.subprocess, "Popen", side_effect=fake_spawn), \
                patch.object(sandbox_runner.os, "killpg") as terminate, \
                patch.object(sandbox_runner.time, "monotonic", side_effect=[0.0, 123.0]):
            try:
                sandbox_runner.run_local(scratch, ROOT / "participant", scratch,
                                         {"budget_seconds": 2, "wall_seconds": 1}, scratch)
            except sandbox_runner.SandboxUnavailable:
                pass
            else:
                raise AssertionError("unaccounted outer timeout became a solver score: " + stderr_kind)
            terminate.assert_called_once()


def check_staged_bootstrap():
    with tempfile.TemporaryDirectory(prefix="staged-worker-", dir="/tmp") as directory:
        local = Path(directory)
        public = local / "public"
        public.mkdir()
        source = "raise RuntimeError('staged-worker-sentinel')\n"
        (local / "worker.py").write_text(source)
        command = sandbox_runner.sandbox_command(local, ROOT / "participant", local,
                                                  "request.json", "state.npz", public)
        assert command[-1] == source, "supervisor and child did not use the same staged revision"


def main():
    for stderr_kind in ("regular", "missing", "symlink"):
        check_outer_timeout(stderr_kind)
    check_staged_bootstrap()
    print('{"passed":4,"failed":0}')


if __name__ == "__main__":
    main()
