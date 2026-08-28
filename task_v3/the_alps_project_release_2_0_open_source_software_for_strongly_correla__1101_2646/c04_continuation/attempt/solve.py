import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import json
import time
from pathlib import Path
import numpy as np
from continuation import continue_matrix, hermitian
from bandfit import try_band_model


def unpack(value):
    return np.asarray(value['real'], dtype=float) + 1j * np.asarray(value['imag'], dtype=float)


def pack(value):
    return {'real': value.real.tolist(), 'imag': value.imag.tolist()}


def solve(request):
    started = time.monotonic()
    data = unpack(request['G_iw'])
    bare = unpack(request['h0'])
    dimension = len(bare)
    identity = np.eye(dimension)
    moments = [hermitian(unpack(value)) for value in request['moments']]
    center = float(np.mean(request['support']))
    scale = max(float(np.diff(request['support'])[0]) / 2, float(request['eta']), 1e-10)
    normalized_moments = [identity, (moments[1] - center * identity) / scale,
                          (moments[2] - 2 * center * moments[1] + center ** 2 * identity) / scale ** 2]
    nodes = (1j * np.asarray(request['iw'], dtype=float) - center) / scale
    physical_points = np.asarray(request['omega'], dtype=float) + 1j * float(request['eta'])
    points = (physical_points - center) / scale
    bound = max(float(request.get('absolute_data_error', 1e-13)), 1e-16) * scale
    metadata = {}
    green = continue_matrix(nodes, data * scale, normalized_moments, points, bound, metadata=metadata)
    if not metadata.get('discrete',False):
        budget = min({2:12,3:30,4:62}.get(dimension,30),100-(time.monotonic()-started))
        if budget > 2:
            try:
                refined = try_band_model(nodes,data*scale,normalized_moments,points,bound,green,seconds=budget,residual=metadata.get('residual'))
                if refined is not None:
                    green = refined
            except (ValueError,np.linalg.LinAlgError,FloatingPointError):
                pass
    green = green / scale
    sigma = physical_points[:, None, None] * identity - bare - np.linalg.inv(green)
    return {'G_retarded': pack(green), 'Sigma_retarded': pack(sigma)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    request = json.loads(Path(arguments.input).read_text())
    result = solve(request)
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
