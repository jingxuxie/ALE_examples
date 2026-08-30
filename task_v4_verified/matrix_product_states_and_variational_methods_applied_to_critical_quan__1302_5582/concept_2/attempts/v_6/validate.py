import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from optimize import Witness
from physics import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tensor', nargs='?', default='state.npz')
    parser.add_argument('--output', default='validation.json')
    arguments = parser.parse_args()
    path = Path(arguments.tensor)
    result = check(path)
    tensor = np.load(path)['A']
    witness = Witness(tensor, full=True)
    with torch.no_grad():
        energy, errors, canonical = witness.evaluate(torch.tensor(witness.initial))
    families = ['order', 'density', 'y', 'composite_order']
    independent = {family: float(error.abs().max()) for family, error in zip(families, errors)}
    independent['energy_excess'] = float(energy)
    independent['canonicalization_change'] = float(torch.linalg.norm(canonical-torch.tensor(tensor)))
    discrepancies = {family: abs(independent[family]-result['metrics'][family+'_max_relative_error']) for family in families}
    result['independent_sector_contractions'] = independent
    result['maximum_checker_discrepancy'] = max(discrepancies.values())
    result['artifact_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    result['artifact_bytes'] = path.stat().st_size
    Path(arguments.output).write_text(json.dumps(result, indent=2)+'\n')
    summary = {key: value for key, value in result.items() if key != 'metrics'}
    summary['metrics'] = {key: value for key, value in result['metrics'].items() if not isinstance(value, list)}
    print(json.dumps(summary, indent=2))
    if not result['passed'] or result['maximum_checker_discrepancy'] > 1e-7:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
