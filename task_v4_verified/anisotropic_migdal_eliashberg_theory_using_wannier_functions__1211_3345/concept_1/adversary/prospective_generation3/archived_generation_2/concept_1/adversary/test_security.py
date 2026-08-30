import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import POLICY, read_output, run_candidate, safe_copy


def instance():
    return {"temperature": np.array(0.03), "n_freq": np.array(7),
            "weights": np.array([0.4, 0.6]), "omega": np.array([1.0]),
            "coupling": np.ones((1, 2, 2)), "coulomb": np.zeros((2, 2)),
            "initial_delta": np.ones((2, 7))}


class OutputValidation(unittest.TestCase):
    def test_valid_and_invalid_arrays(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output.npz"
            for dtype in (np.float64, np.float32):
                np.savez(output, delta=np.ones((2, 7), dtype=dtype), z=np.ones((2, 7), dtype=dtype))
                self.assertEqual(read_output(output, (2, 7))["delta"].shape, (2, 7))
            invalids = [np.ones((2, 8)), np.ones((2, 7), dtype=object), np.ones((2, 7), dtype=complex),
                        np.full((2, 7), np.nan), np.full((2, 7), np.inf)]
            for invalid in invalids:
                np.savez(output, delta=invalid, z=np.ones((2, 7)))
                with self.assertRaises(ValueError):
                    read_output(output, (2, 7))

    def test_symlink_and_hardlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.npz"
            link = Path(temporary) / "link.npz"
            np.savez(source, delta=np.ones((2, 7)), z=np.ones((2, 7)))
            link.symlink_to(source)
            with self.assertRaises(OSError):
                read_output(link, (2, 7))
            link.unlink()
            os.link(source, link)
            with self.assertRaises(ValueError):
                read_output(link, (2, 7))

    def test_archive_bomb_and_duplicate_members_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.npz"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("delta.npy", bytes(POLICY["output_bytes_max"] + 1))
                archive.writestr("z.npy", b"x")
            with self.assertRaises(ValueError):
                read_output(path, (2, 7))
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("delta.npy", b"x")
                archive.writestr("z.npy", b"x")
                archive.writestr("other.npy", b"x")
            with self.assertRaises(ValueError):
                read_output(path, (2, 7))

    def test_oversized_header_shape_rejected_before_allocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.npz"
            buffer = io.BytesIO()
            np.lib.format.write_array_header_1_0(buffer, {"descr": "<f8", "fortran_order": False, "shape": (10 ** 12, 7)})
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("delta.npy", buffer.getvalue())
                archive.writestr("z.npy", buffer.getvalue())
            with self.assertRaises(ValueError):
                read_output(path, (2, 7))

    def test_submission_symlink_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / "solve.py").symlink_to(ROOT / "evaluator" / "hidden" / "policy.json")
            with self.assertRaises(ValueError):
                safe_copy(source, Path(temporary) / "copied")

    def test_submission_root_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.symlink_to(ROOT / "evaluator" / "hidden", target_is_directory=True)
            with self.assertRaises(ValueError):
                safe_copy(source, Path(temporary) / "copied")


class Isolation(unittest.TestCase):
    def candidate(self, text, **limits):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "solve.py").write_text(text)
            return run_candidate(directory, instance(), **limits)

    def test_files_network_process_and_thread_denials(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as private:
            canary = Path(private) / "canary.txt"
            canary.write_text("PRIVATE_CANARY_NOT_AN_INPUT")
            code = """import argparse, ctypes, os, socket, threading
import numpy as np
parser=argparse.ArgumentParser()
parser.add_argument('--input'); parser.add_argument('--output')
args=parser.parse_args()
blocked=[]
try:
    open(CANARY).read()
    blocked.append(False)
except PermissionError:
    blocked.append(True)
try:
    socket.socket()
    blocked.append(False)
except PermissionError:
    blocked.append(True)
try:
    child=os.fork()
    if child == 0:
        os._exit(0)
    os.waitpid(child,0)
    blocked.append(False)
except PermissionError:
    blocked.append(True)
try:
    worker=threading.Thread(target=lambda: None)
    worker.start(); worker.join()
    blocked.append(False)
except (RuntimeError, PermissionError):
    blocked.append(True)
array=np.zeros((2,7)); array[0,:4]=blocked
np.savez(args.output,delta=array,z=np.ones((2,7)))
""".replace("CANARY", repr(str(canary)))
            result, execution = self.candidate(code)
            self.assertIsNotNone(result, execution)
            self.assertTrue(np.all(result["delta"][0, :4] == 1), result["delta"][0, :4])
            self.assertEqual(canary.read_text(), "PRIVATE_CANARY_NOT_AN_INPUT")

    def test_candidate_not_imported_and_timer_not_trusted(self):
        code = """import argparse,json,sys
import numpy as np
parser=argparse.ArgumentParser(); parser.add_argument('--input'); parser.add_argument('--output'); args=parser.parse_args()
assert not any('physics' == name or 'evaluate' == name for name in sys.modules)
print(json.dumps({'candidate_cpu_seconds':-10000}),file=sys.stderr)
np.savez(args.output,delta=np.ones((2,7)),z=np.ones((2,7)))
"""
        result, execution = self.candidate(code)
        self.assertIsNotNone(result, execution)
        self.assertGreater(execution["cpu_seconds"], 0)

    def test_output_symlink_to_private_is_rejected(self):
        code = """import argparse,os
parser=argparse.ArgumentParser(); parser.add_argument('--input'); parser.add_argument('--output'); args=parser.parse_args()
os.symlink(TARGET,args.output)
""".replace("TARGET", repr(str(ROOT / "evaluator" / "hidden" / "policy.json")))
        result, execution = self.candidate(code)
        self.assertIsNone(result)
        self.assertIn("symlink", execution["error"])

    def test_wall_timeout(self):
        result, execution = self.candidate("import time\ntime.sleep(60)\n", wall_seconds=0.5)
        self.assertIsNone(result)
        self.assertTrue(execution["wall_timeout"])

    def test_cpu_timeout(self):
        result, execution = self.candidate("while True:\n    pass\n", cpu_seconds=1, wall_seconds=120)
        self.assertIsNone(result)
        self.assertNotEqual(execution["returncode"], 0)


if __name__ == "__main__":
    unittest.main()
