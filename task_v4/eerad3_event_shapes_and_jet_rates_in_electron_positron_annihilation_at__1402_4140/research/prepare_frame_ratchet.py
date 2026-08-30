import json
import shutil
from datetime import datetime, timezone

import numpy as np

from frame_challenge import CONCEPT, high_precision_check, transform


def main():
    snapshot = CONCEPT / 'adversary/generation_2_snapshot'
    assert not snapshot.exists()
    status = json.loads((CONCEPT / 'status.json').read_text())
    status['status'] = 'solved'
    status['fresh_attempts'].append({
        'attempt': 2, 'generation': 2,
        'evaluation': json.loads((CONCEPT / 'attempts/v_2.evaluation.json').read_text())})
    (CONCEPT / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    snapshot.mkdir()
    for name in ['participant', 'evaluator']:
        shutil.copytree(CONCEPT / name, snapshot / name)
    shutil.copyfile(CONCEPT / 'status.json', snapshot / 'status.json')
    data = dict(np.load(snapshot / 'evaluator/hidden/test.npz', allow_pickle=False))
    frames = np.empty(len(data['s']), dtype=np.int64)
    generator = np.random.default_rng(819228773)
    for family in range(5):
        selected = np.flatnonzero(data['family'] == family)
        assignments = np.tile(np.arange(4), len(selected) // 4)
        generator.shuffle(assignments)
        frames[selected] = assignments
    original = data['p']
    data['p'], axes, gammas = transform(original, frames, 893792332)
    data['frame'] = frames
    rounding_error = high_precision_check(original, data['p'], axes, gammas, frames)
    np.savez_compressed(CONCEPT / 'evaluator/hidden/test.npz', **data)
    validation = dict(np.load(CONCEPT / 'participant/input/validation.npz', allow_pickle=False))
    frame_validation = {name: np.concatenate([values] * 4) for name, values in validation.items()}
    frame_validation['frame'] = np.repeat(np.arange(4), len(validation['p']))
    frame_validation['p'], _, _ = transform(frame_validation['p'], frame_validation['frame'], 439277111)
    np.savez_compressed(CONCEPT / 'participant/input/frame_validation.npz', **frame_validation)
    provenance = {
        'generation': 3, 'cases': len(frames), 'phase_frame_groups': 20,
        'per_group': 10000, 'latent_source': 'generation_2_snapshot/evaluator/hidden/test.npz',
        'labels': 'unchanged quadruple-precision native evaluation of authoritative s',
        'frame_assignment_seed': 819228773, 'hidden_transform_seed': 893792332,
        'public_transform_seed': 439277111,
        'boost_vs_100_digit_max_relative_vector_error': rounding_error,
        'frame_groups': ['CM', 'canonical_axes', 'moderate_boost', 'large_boost'],
        'gamma_ranges': {'moderate_boost': [10, 1000], 'large_boost': [100000, 100000000]},
        'target_fixed_before_launch': True,
        'prepared_at': datetime.now(timezone.utc).isoformat()}
    (CONCEPT / 'adversary/generation_3_data_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
