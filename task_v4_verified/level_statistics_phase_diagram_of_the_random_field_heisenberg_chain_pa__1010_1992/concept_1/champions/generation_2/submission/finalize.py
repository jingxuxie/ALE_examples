import hashlib
import json
from pathlib import Path

required = ('predict.py', 'model.npz', 'runtime_features.py', 'descriptors.py')
metrics = json.loads(Path('final_metrics.json').read_text())
holdout = json.loads(Path('final_holdout.json').read_text())
repeat = json.loads(Path('final_runtime_repeat.json').read_text())
assert metrics['training_records'] == 3360
assert metrics['seeds'] == 8
assert holdout['records_scored'] == 320 and holdout['offset'] == 1280
assert holdout['overall_rmse'] <= .035 and holdout['worst_family_rmse'] <= .05
assert holdout['protocol_valid'] and holdout['resource_valid']
assert repeat['protocol_valid'] and repeat['resource_valid']
manifest = {
    'entry_point': 'predict.py',
    'runtime_dependencies': ['Python 3', 'NumPy'],
    'assets': {name: {'bytes': Path(name).stat().st_size, 'sha256': hashlib.sha256(Path(name).read_bytes()).hexdigest()} for name in required},
    'training_records': metrics['training_records'],
    'held_out_overall_rmse': holdout['overall_rmse'],
    'held_out_worst_family_rmse': holdout['worst_family_rmse'],
    'held_out_records': holdout['records_scored'],
    'inference_seconds': [holdout['inference_seconds'], repeat['inference_seconds']],
    'startup_seconds': [holdout['startup_seconds'], repeat['startup_seconds']],
    'address_space_limit_mib': 2048,
    'cpu_affinity_cores': 4,
    'local_checks_passed': True,
    'private_evaluation_performed': False,
}
Path('submission_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
