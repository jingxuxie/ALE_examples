"""Black-box runtime checks; fixtures stay under the task's adversary directory."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

from isolation import sandbox_command


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hubbard-isolation-", dir=str(Path(__file__).resolve().parents[1] / "adversary"))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.participant = self.root / "participant"
        self.submission = self.root / "submission"
        self.scratch = self.root / "scratch"
        for directory in (self.participant, self.submission, self.scratch):
            directory.mkdir()
        self.hidden = self.root / "hidden-sentinel"
        self.hidden.write_text("PRIVATE_SENTINEL_UNCHANGED")
        (self.participant / "public_probe.py").write_text("VALUE = 173\n")
        (self.submission / "submission_probe.py").write_text("VALUE = 227\n")
        self.environment = dict(os.environ, PYTHONPATH=str(self.participant),
                                OPENAI_API_KEY="DO_NOT_INHERIT", AWS_SECRET_ACCESS_KEY="SECRET",
                                LD_PRELOAD="/does/not/exist", PYTHONSTARTUP=str(self.hidden))

    def launch(self, command, **options):
        arguments, environment = sandbox_command(
            command, self.environment, self.participant, self.submission, self.scratch,
            **options)
        return subprocess.Popen(arguments, env=environment, cwd=self.submission,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)

    def execute(self, code, arguments=(), **options):
        process = self.launch(["/usr/bin/python3", "-c", textwrap.dedent(code),
                               *map(str, arguments)], **options)
        try:
            output, error = process.communicate(timeout=60)
        except BaseException:
            process.kill()
            process.communicate(timeout=10)
            raise
        self.assertEqual(process.returncode, 0, error.decode(errors="replace"))
        return output.decode()

    def test_scientific_imports_and_public_pythonpath(self):
        output = self.execute("""
            import json, numpy, scipy, scipy.linalg, scipy.optimize
            import public_probe, submission_probe
            assert public_probe.VALUE == 173 and submission_probe.VALUE == 227
            assert numpy.allclose(scipy.linalg.solve(numpy.eye(2), numpy.ones(2)), 1)
            result = scipy.optimize.minimize(lambda values: (values[0] - 2) ** 2, [0.])
            assert result.fun < 1e-10
            print(json.dumps([numpy.__version__, scipy.__version__]))
        """)
        self.assertEqual(json.loads(output), ["1.21.5", "1.8.0"])

    def test_python_script_entrypoint(self):
        script = self.submission / "policy.py"
        script.write_text("import numpy, public_probe; print('SCRIPT_OK', public_probe.VALUE)\n")
        process = self.launch(["/usr/bin/python3", "-B", "-u", str(script)])
        output, error = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 0, error.decode())
        self.assertEqual(output.strip(), b"SCRIPT_OK 173")

    def test_denials_and_scratch_writes(self):
        output = self.execute("""
            import errno, json, os, pathlib, socket, sys
            hidden, participant, submission, scratch = map(pathlib.Path, sys.argv[1:])
            denied = []
            def reject(name, operation):
                try:
                    operation()
                except OSError as error:
                    assert error.errno in (errno.EACCES, errno.EPERM, errno.ENOSYS)
                    denied.append(name)
                else:
                    raise AssertionError(name + " unexpectedly permitted")
            reject("hidden_read", hidden.read_bytes)
            reject("hidden_write", lambda: hidden.write_text("CORRUPTED"))
            reject("outside_create", lambda: (hidden.parent / "outside").write_text("bad"))
            reject("participant_write", lambda: (participant / "public_probe.py").write_text("bad"))
            reject("submission_write", lambda: (submission / "submission_probe.py").write_text("bad"))
            reject("proc_environ", lambda: pathlib.Path("/proc/self/environ").read_bytes())
            reject("proc_parent", lambda: pathlib.Path(f"/proc/{os.getppid()}/environ").read_bytes())
            reject("truncate", lambda: os.truncate(hidden, 0))
            reject("readonly_truncate_open", lambda: os.open(hidden, os.O_RDONLY | os.O_TRUNC))
            reject("chmod", lambda: os.chmod(hidden, 0o777))
            reject("network_inet", lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            reject("network_inet6", lambda: socket.socket(socket.AF_INET6, socket.SOCK_STREAM))
            reject("network_unix", lambda: socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
            reject("fork", os.fork)
            reject("affinity_expand", lambda: os.sched_setaffinity(0, {0, 1}))
            (scratch / "link").symlink_to(hidden)
            reject("symlink_read", lambda: (scratch / "link").read_bytes())
            reject("symlink_write", lambda: (scratch / "link").write_text("bad"))
            (scratch / "output").write_text("writable")
            assert (scratch / "output").read_text() == "writable"
            print(json.dumps(denied))
        """, [self.hidden, self.participant, self.submission, self.scratch])
        self.assertEqual(len(json.loads(output)), 17)
        self.assertEqual(self.hidden.read_text(), "PRIVATE_SENTINEL_UNCHANGED")
        self.assertFalse((self.root / "outside").exists())

    def test_environment_and_limits(self):
        output = self.execute("""
            import json, os, resource
            assert not any("SECRET" in name or "TOKEN" in name or "API_KEY" in name
                           for name in os.environ)
            assert "LD_PRELOAD" not in os.environ and "PYTHONSTARTUP" not in os.environ
            assert len(os.sched_getaffinity(0)) == 1
            assert resource.getrlimit(resource.RLIMIT_AS) == (2147483648, 2147483648)
            assert resource.getrlimit(resource.RLIMIT_CPU) == (180, 180)
            try:
                bytearray(3 * 1024 ** 3)
            except MemoryError:
                pass
            else:
                raise AssertionError("memory limit not enforced")
            print("LIMITS_OK")
        """)
        self.assertEqual(output.strip(), "LIMITS_OK")

    def test_extra_inherited_descriptor_is_closed(self):
        with self.hidden.open("rb") as stream:
            code = "import os,sys; descriptor=int(sys.argv[1]);\ntry: os.read(descriptor,1)\nexcept OSError: print('FD_CLOSED')\nelse: raise AssertionError('leaked descriptor')"
            arguments, environment = sandbox_command(
                ["/usr/bin/python3", "-c", code, str(stream.fileno())], self.environment,
                self.participant, self.submission, self.scratch)
            process = subprocess.Popen(arguments, env=environment, cwd=self.submission,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, pass_fds=(stream.fileno(),),
                                       start_new_session=True)
            output, error = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, error.decode())
            self.assertEqual(output.strip(), b"FD_CLOSED")

    def test_cpu_budget_kills_payload(self):
        process = self.launch(["/usr/bin/python3", "-c", "while True: pass"], cpu_seconds=1)
        process.communicate(timeout=20)
        self.assertEqual(process.returncode, 128 + signal.SIGKILL)

    def test_writable_input_descriptor_is_rejected(self):
        source = self.participant / "public_probe.py"
        arguments, environment = sandbox_command(
            ["/usr/bin/python3", "-c", "import os; os.write(0,b'CORRUPTED')"],
            self.environment, self.participant, self.submission, self.scratch)
        with source.open("r+b") as stream:
            process = subprocess.Popen(arguments, env=environment, cwd=self.submission,
                                       stdin=stream, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True)
            output, error = process.communicate(timeout=20)
        self.assertEqual(process.returncode, 125, (output, error))
        self.assertEqual(source.read_text(), "VALUE = 173\n")

    def test_setup_failure_never_runs_payload(self):
        marker = self.scratch / "must-not-exist"
        arguments, environment = sandbox_command(
            ["/usr/bin/python3", "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()",
             str(marker)], self.environment, self.participant, self.submission, self.scratch)
        wrapper = textwrap.dedent("""
            import json, pathlib, sys
            sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
            import isolation as sandbox
            def unavailable(*arguments):
                raise OSError("simulated unavailable Landlock")
            sandbox._landlock = unavailable
            raise SystemExit(sandbox._launch(json.loads(sys.argv[2])))
        """)
        process = subprocess.Popen(["/usr/bin/python3", "-I", "-B", "-S", "-c", wrapper,
                                    arguments[-3], arguments[-1]], env=environment,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        output, error = process.communicate(timeout=20)
        self.assertEqual(process.returncode, 125, (output, error))
        self.assertIn(b"simulated unavailable Landlock", error)
        self.assertFalse(marker.exists())

    def test_supervisor_kill_closes_payload_pipes(self):
        process = self.launch(["/usr/bin/python3", "-c",
                               "import os,time; print(os.getpid(),flush=True); time.sleep(120)"])
        try:
            payload_pid = int(process.stdout.readline())
            process.kill()
            process.communicate(timeout=10)
            status = Path(f"/proc/{payload_pid}/stat")
            for attempt in range(30):
                if not status.exists() or status.read_text().split(") ", 1)[1].startswith("Z "):
                    break
                time.sleep(0.05)
            else:
                self.fail("payload survived supervisor death")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)

    def test_native_submission(self):
        source = self.submission / "probe.cpp"
        binary = self.submission / "probe"
        source.write_text(textwrap.dedent("""
            #include <cstdio>
            #include <fcntl.h>
            #include <sys/socket.h>
            #include <unistd.h>
            int main(int count, char **arguments) {
                if (count != 3 || open(arguments[1], O_RDONLY) >= 0) return 1;
                if (socket(AF_INET, SOCK_STREAM, 0) >= 0) return 2;
                int descriptor = open(arguments[2], O_CREAT | O_WRONLY, 0600);
                if (descriptor < 0 || write(descriptor, "ok", 2) != 2) return 3;
                close(descriptor);
                std::puts("NATIVE_OK");
                return 0;
            }
        """))
        subprocess.run(["/usr/bin/g++", "-O2", str(source), "-o", str(binary)],
                       check=True, capture_output=True, timeout=60,
                       env=dict(os.environ, TMPDIR=str(self.scratch)))
        process = self.launch([str(binary), str(self.hidden), str(self.scratch / "native-output")])
        output, error = process.communicate(timeout=20)
        self.assertEqual(process.returncode, 0, error.decode())
        self.assertEqual(output.strip(), b"NATIVE_OK")

    def test_unsafe_pythonpath_and_scratch_are_rejected(self):
        with self.assertRaises(ValueError):
            sandbox_command(["/usr/bin/true"], {"PYTHONPATH": str(self.root)},
                            self.participant, self.submission, self.scratch)
        with self.assertRaises(ValueError):
            sandbox_command(["/usr/bin/true"], {}, self.participant,
                            self.submission, self.submission)

    def test_public_asset_environment_is_validated(self):
        assets = self.participant / "input"
        assets.mkdir()
        (assets / "public.json").write_text("{\"value\": 173}")
        self.environment["HUBBARD_ASSET_DIR"] = str(assets)
        output = self.execute("""
            import json, os, pathlib
            assets = pathlib.Path(os.environ["HUBBARD_ASSET_DIR"])
            assert json.loads((assets / "public.json").read_text())["value"] == 173
            print("ASSETS_OK")
        """)
        self.assertEqual(output.strip(), "ASSETS_OK")
        with self.assertRaises(ValueError):
            sandbox_command(["/usr/bin/true"], {"HUBBARD_ASSET_DIR": str(self.root)},
                            self.participant, self.submission, self.scratch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
