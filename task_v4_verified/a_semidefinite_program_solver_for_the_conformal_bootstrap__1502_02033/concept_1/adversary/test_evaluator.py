import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from oracle import InvalidResult, LebesgueOracle, strict_json, validate_nodes
from runner import run_solution


class NumericalChecks(unittest.TestCase):
    def setUp(self):
        self.case = {"degree": 2, "scenarios": [{"a": 1.0, "poles": []}, {"a": 1.1, "poles": [0.2]}]}

    def test_invalid_nodes_and_claims(self):
        invalid = [[], [0, 1], [0, 1, 1], [0, 2, 1], [-1, 1, 2],
                   [0, True, 2], [0, "1", 2], [0, float("nan"), 2],
                   [0, 1, float("inf")], [0, 1, 1 + 1e-15], [0, 1, 1e200]]
        for nodes in invalid:
            with self.subTest(nodes=nodes), self.assertRaises(InvalidResult):
                validate_nodes(self.case, {"nodes": nodes})
        with self.assertRaises(InvalidResult):
            validate_nodes(self.case, {"nodes": [0, 1, 2], "score": 1e300})

    def test_strict_json(self):
        for text in ('{"nodes":[NaN]}', '{"nodes":[],"nodes":[0,1,2]}', '{"nodes":[Infinity]}'):
            with self.assertRaises(InvalidResult):
                strict_json(text)
        with self.assertRaises(InvalidResult):
            validate_nodes(self.case, strict_json('{"nodes":[0,1,1e999]}'))

    def test_tail_analytic_peak(self):
        gap = 0.02
        case = {"degree": 1, "scenarios": [{"a": 1.0, "poles": []}]}
        oracle = LebesgueOracle(case, {"nodes": [0, gap]})
        measured = oracle.supremum()
        slope_inside = math.expm1(gap) / gap
        slope_outside = (1 + math.exp(gap)) / gap
        inside = 1 - 1 / slope_inside
        outside = 1 + 1 / slope_outside
        exact = max(1.0, math.exp(-inside) * (1 + slope_inside * inside),
                    math.exp(-outside) * (slope_outside * outside - 1))
        self.assertLessEqual(measured["lebesgue_lower"], exact * (1 + 1e-10))
        self.assertGreaterEqual(measured["lebesgue_upper"], exact * (1 - 1e-10))
        self.assertGreater(measured["peak_x"], 20 * gap)
        self.assertLess(measured["relative_enclosure"], 8.01e-5)
        tail_points = np.linspace(measured["tail_start"], measured["tail_start"] + 20, 100)
        self.assertTrue(np.all(np.diff(oracle.values(tail_points)[0]) < 0))

    def test_interval_enclosures_and_high_precision(self):
        oracle = LebesgueOracle(self.case, {"nodes": [0.03, 0.7, 2.9]})
        boundaries = [0.0, 0.03, 0.7, 2.9, 10.9]
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            ends = oracle.values([left, right])
            bound = oracle.upper_bound(left, right, ends[:, 0], ends[:, 1])
            self.assertLessEqual(float(oracle.values(np.linspace(left, right, 257)).max()), bound)
        for position in (0.0, 0.031, 0.4, 1.2, 4.5):
            for scenario in range(2):
                self.assertAlmostEqual(float(oracle.values([position])[scenario, 0]),
                                       oracle.mp_value(position, scenario), places=11)
        result = oracle.supremum()
        dense = float(oracle.values(np.linspace(0, 11, 10001)).max())
        self.assertLessEqual(dense, result["log_upper"])

    def test_weight_scaling_and_underflow(self):
        nodes = [0.0, 0.0008, 0.7]
        case = {"degree": 2, "scenarios": [{"a": 0.4, "poles": [1e-6] * 12}]}
        oracle = LebesgueOracle(case, {"nodes": nodes})
        scaled = {"degree": 2, "scenarios": [{"a": 4.0, "poles": [1e-7] * 12}]}
        alternate = LebesgueOracle(scaled, {"nodes": [node / 10 for node in nodes]})
        points = np.array([0.0, 0.01, 0.5, 100000.0])
        np.testing.assert_allclose(oracle.values(points), alternate.values(points), atol=1e-10)
        self.assertTrue(np.isfinite(oracle.values(points)).all())

    def test_budget_exhaustion_fails_closed(self):
        with self.assertRaisesRegex(InvalidResult, "unresolved"):
            LebesgueOracle(self.case, {"nodes": [0, 1, 2]}).supremum(max_splits=0)


class IsolationChecks(unittest.TestCase):
    def probe(self, program):
        with tempfile.TemporaryDirectory(prefix="probe_", dir=ROOT / "adversary") as directory:
            path = Path(directory) / "solution.py"
            path.write_text(program, encoding="utf-8")
            return run_solution(path, '{"degree":2,"scenarios":[{"a":1,"poles":[]}]}')

    def test_private_files_network_fork_and_cwd(self):
        program = (
            "import json, os, pathlib, socket, sys\n"
            "assert os.getcwd() == '/work'\n"
            "assert not pathlib.Path('/srv').exists() and not pathlib.Path('/home').exists()\n"
            "assert not pathlib.Path('/submission/../../evaluator').exists()\n"
            "assert socket.if_nameindex() == [(1, 'lo')]\n"
            "try:\n"
            " os.fork()\n"
            "except OSError:\n"
            " pass\n"
            "else:\n"
            " raise AssertionError('fork unexpectedly allowed')\n"
            "json.dump({'nodes':[0,1,2]}, open(sys.argv[2], 'w'))\n"
        )
        output, diagnostics = self.probe(program)
        self.assertEqual(output, {"nodes": [0, 1, 2]})
        self.assertLess(diagnostics["cpu_seconds"], 8)

    def test_symlink_escape_rejected(self):
        with self.assertRaisesRegex(InvalidResult, "regular file"):
            self.probe("import os,sys\nos.symlink('../../reference.json',sys.argv[2])\n")

    def test_fifo_rejected_without_blocking(self):
        with self.assertRaisesRegex(InvalidResult, "regular file"):
            self.probe("import os,sys\nos.mkfifo(sys.argv[2])\n")

    def test_oversized_output_rejected(self):
        with self.assertRaisesRegex(InvalidResult, "oversized"):
            self.probe("import sys\nopen(sys.argv[2],'w').write('0'*70000)\n")

    def test_private_bundle_refused(self):
        with self.assertRaisesRegex(InvalidResult, "private evaluator"):
            run_solution(ROOT / "evaluator" / "evaluate.py", "{}")


class ResourceAccountingChecks(unittest.TestCase):
    def test_direct_child_cpu_and_protected_report(self):
        source = (
            "import json,os,sys,time\n"
            "started=time.process_time()\n"
            "while time.process_time()-started<0.4: pass\n"
            "print(json.dumps({'cpu_seconds':0,'returncode':0}))\n"
            "open('/work/resources.json','w').write('{\"cpu_seconds\":0}')\n"
            "try:\n"
            " descriptor=os.open('/proc/'+str(os.getppid())+'/fd/1',os.O_WRONLY)\n"
            " raise RuntimeError('resource channel was accessible')\n"
            "except OSError: pass\n"
            "json.dump({'nodes':[0,1,2]},open(sys.argv[2],'w'))\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            path = Path(directory) / "solution.py"
            path.write_text(source)
            output, timing = run_solution(path, "{}")
        self.assertEqual(output, {"nodes": [0, 1, 2]})
        self.assertGreaterEqual(timing["cpu_seconds"], 0.39)
        self.assertLess(timing["cpu_seconds"], 2.0)


if __name__ == "__main__":
    unittest.main()
