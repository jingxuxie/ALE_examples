import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from pair_model import CASOracle, FAMILIES, initial_observation, increments, sample_model


def build(count, offset):
    models, tables, diagnostics = [], [], []
    for index in range(count):
        family = FAMILIES[index % len(FAMILIES)]
        model = sample_model(offset + index * 7919, family)
        oracle = CASOracle(model)
        models.append(model)
        tables.append(oracle.all_energies())
        diagnostics.append(oracle.spectrum())
    return models, np.asarray(tables), diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hidden-count", type=int, default=120)
    arguments = parser.parse_args()
    hidden = ROOT / "evaluator/hidden"
    public = ROOT / "participant/input"
    hidden.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    private_models, tables, diagnostics = build(arguments.hidden_count, 946702511)
    np.savez_compressed(hidden / "cases.npz", energies=tables)
    (hidden / "models.json").write_text(json.dumps(private_models))
    (hidden / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
    public_models, public_tables, public_diagnostics = build(36, 76191)
    np.savez_compressed(public / "practice.npz", energies=public_tables)
    (public / "practice_models.json").write_text(json.dumps(public_models))
    (public / "practice_diagnostics.json").write_text(json.dumps(public_diagnostics, indent=2))
    summary = {}
    for family_index, family in enumerate(FAMILIES):
        selected = tables[family_index::len(FAMILIES)]
        second_errors, third_errors, absolute_sums = [], [], []
        for table in selected:
            values = increments(table)
            second_errors.append(sum(value for mask, value in enumerate(values) if mask.bit_count() <= 2) - table[-1])
            third_errors.append(sum(value for mask, value in enumerate(values) if mask.bit_count() <= 3) - table[-1])
            absolute_sums.append(sum(abs(value) for mask, value in enumerate(values) if mask.bit_count() >= 3))
        summary[family] = {"mbe2_rmse": float(np.sqrt(np.mean(np.square(second_errors)))),
                           "mbe3_rmse": float(np.sqrt(np.mean(np.square(third_errors)))),
                           "higher_absolute_sum_mean": float(np.mean(absolute_sums))}
    (hidden / "generation_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
