import importlib.util
import io
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np


def main():
    concept = Path(__file__).resolve().parents[1]
    specification = importlib.util.spec_from_file_location('prediction_evaluator', concept / 'evaluator/evaluate.py')
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    quality = json.loads((concept / 'evaluator/hidden/quality.json').read_text())
    data = np.load(concept / 'evaluator/hidden/test.npz', allow_pickle=False)
    labels = data['log_weight']
    families = data['family']
    frames = data['frame']
    counts = {f'{family}/{frame}': int(np.sum((families == family) & (frames == frame)))
              for family in range(5) for frame in range(4)}
    assert set(counts.values()) == {10000}
    assert np.isfinite(data['p']).all() and np.all(data['p'][:, :, 3] > 0)
    assert np.all(data['s'] > 1e-10) and np.max(np.abs(data['s'].sum(axis=1) - 1)) < 1e-12
    controls = {}
    controls['exact'] = module.score(labels.copy(), labels, families, frames, quality)['passed']
    for family in range(5):
        for frame in range(4):
            prediction = labels.copy()
            prediction[(families == family) & (frames == frame)] += 1e-6
            controls[f'bad_{family}_{frame}'] = module.score(prediction, labels, families, frames, quality)['passed']
    for name, prediction in [('constant', np.zeros_like(labels)), ('biased', labels + 1e-8),
                             ('shuffled', labels[::-1]), ('nan', np.full_like(labels, np.nan)),
                             ('wrong_shape', labels[:-1])]:
        try:
            controls[name] = module.score(prediction, labels, families, frames, quality)['passed']
        except ValueError:
            controls[name] = False
    assert controls['exact'] and not any(value for name, value in controls.items() if name != 'exact')
    archive_controls = {}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'output.npz'
        np.savez(path, log_weight=labels)
        archive_controls['valid_round_trip'] = np.array_equal(module.load_prediction(path, len(labels)), labels)
        for name, values in [('bad_shape', labels[:10]), ('bad_dtype', labels.astype(np.float32))]:
            np.savez(path, log_weight=values)
            try:
                module.load_prediction(path, len(labels))
                archive_controls[name] = False
            except ValueError:
                archive_controls[name] = True
        stream = io.BytesIO()
        np.lib.format.write_array_header_1_0(stream, {'descr': '<f8', 'fortran_order': False, 'shape': (10 ** 12,)})
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('log_weight.npy', stream.getvalue())
        try:
            module.load_prediction(path, len(labels))
            archive_controls['allocation_bomb_rejected'] = False
        except ValueError:
            archive_controls['allocation_bomb_rejected'] = True
    assert all(archive_controls.values())
    public = np.load(concept / 'participant/input/frame_validation.npz', allow_pickle=False)
    assert np.array_equal(public['s'][:1500], public['s'][1500:3000])
    assert np.array_equal(public['log_weight'][:1500], public['log_weight'][4500:])
    report = {'cases': len(labels), 'phase_frame_counts': counts, 'controls': controls,
              'archive_controls': archive_controls,
              'all_controls_correct': True, 'authoritative_s_positive_normalized': True,
              'transformed_vectors_finite_future_directed': True,
              'public_frame_labels_invariant': True,
              'transform_precision_validation': 'generation_3_data_provenance.json'}
    (concept / 'adversary/generation_3_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
