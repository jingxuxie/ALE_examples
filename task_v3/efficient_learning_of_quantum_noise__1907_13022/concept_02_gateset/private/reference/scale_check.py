import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

from generate import ROOT, build_case, save_npz, topology
from metrics import losses, score_components
from weak_baseline import solve as weak_solve

sys.path.insert(0, str(ROOT / 'private'))
from evaluator import run_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qubits', type=int, nargs='+', default=[20, 24])
    parser.add_argument('--families', nargs='+', default=['parallel_crosstalk'])
    parser.add_argument('--output', type=Path, default=ROOT / 'private/reference/scale_probe.json')
    arguments = parser.parse_args()
    records = []
    for family in arguments.families:
        for qubits in arguments.qubits:
            started = time.monotonic()
            data, oracle, dimensions = build_case(982412 + qubits, qubits, family, 4)
            geometry = topology(data)
            if geometry['ideal_graph_component_sizes'] != [qubits]:
                raise AssertionError('Large test is not genuinely coupled')
            with tempfile.TemporaryDirectory(prefix='gateset-scale-') as temporary:
                path = Path(temporary) / 'input.npz'
                save_npz(path, data)
                telemetry = {}
                output, runtime = run_case(ROOT / 'private/reference/solver.py', path,
                                           dimensions['queries'], dimensions['holdout_experiments'], telemetry)
            strong = losses(output, oracle)
            weak = losses(weak_solve(data), oracle)
            components, score = score_components(strong, weak, strong)
            passed = (score > 0.9 and runtime < 120 and telemetry['peak_memory_mib'] < 3072
                      and strong['heldout_prediction'] < 0.0016 and strong['identification'] == 0)
            record = dict(family=family, **dimensions, **geometry, **telemetry,
                          runtime=runtime, build_and_test_seconds=time.monotonic() - started,
                          reference_score=score, components=components, reference_losses=strong,
                          weak_losses=weak, passed=bool(passed))
            records.append(record)
            arguments.output.write_text(json.dumps({'cases': records}, indent=2) + '\n')
            print(json.dumps(record), flush=True)
            if not passed:
                raise AssertionError('Large coupled reference failed acceptance checks')


if __name__ == '__main__':
    main()
