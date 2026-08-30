import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import numpy as np
from experiment import read, ROOT
from runtime_features import feature_matrix
from features import feature_matrix as research_features
from predict import load_model, estimate, predict_cases

cases = read(ROOT / 'train.jsonl')[:32]
features = feature_matrix(cases)
np.testing.assert_allclose(features, research_features(cases, kind='quick_particle'), rtol=1e-11, atol=1e-11)
for transform in (lambda fields: np.roll(fields, 5), lambda fields: fields[::-1], lambda fields: -fields, lambda fields: fields + 12.3):
    transformed = [dict(case, fields=transform(np.array(case['fields'])).tolist()) for case in cases]
    np.testing.assert_allclose(features, feature_matrix(transformed), rtol=1e-8, atol=1e-9)
    np.testing.assert_allclose(estimate(features, load_model()), estimate(feature_matrix(transformed), load_model()), rtol=1e-5, atol=1e-6)
assert predict_cases([], load_model()) == {'predictions': []}
for case in cases[:5]:
    batch = predict_cases([case], load_model())
    assert len(batch['predictions']) == 1
    assert 0 <= batch['predictions'][0]['f'] <= 1
import torch
from torch import nn
torch.set_num_threads(1)
asset = load_model()
native_predictions = []
transformed = np.sign(features) * np.log1p(np.abs(features))
for index in range(int(asset['count'])):
    prefix = str(index) + '_'
    network = nn.Sequential(nn.Linear(features.shape[1], 96), nn.SiLU(), nn.Dropout(.04), nn.Linear(96, 48), nn.SiLU(), nn.Dropout(.04), nn.Linear(48, 1), nn.Sigmoid())
    network.load_state_dict({name: torch.tensor(asset[prefix + name]) for name in network.state_dict()})
    network.eval()
    inputs = torch.tensor(np.clip((transformed - asset[prefix + 'mean']) / asset[prefix + 'scale'], -10, 10), dtype=torch.float32)
    with torch.no_grad():
        native_predictions.append(network(inputs).numpy().ravel())
np.testing.assert_allclose(estimate(features, asset), np.mean(native_predictions, axis=0), rtol=2e-6, atol=2e-7)
print('PASS: feature parity, physical symmetries, empty/singleton batches, and NumPy/PyTorch export parity')
