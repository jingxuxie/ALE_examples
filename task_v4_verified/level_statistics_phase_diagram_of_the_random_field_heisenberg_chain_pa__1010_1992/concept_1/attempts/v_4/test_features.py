import gzip
import os
import pickle
import unittest
from pathlib import Path
import numpy as np
from data_io import read
from features import feature_matrix
from structure import structure_features
from predict import predict_chunk, assemble
from transforms import transform
from native_features import describe_cases


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = read(Path(os.environ['SRC']) / 'input' / 'validation.jsonl')[:12]
        with gzip.open('model.pkl.gz', 'rb') as stream:
            cls.bundle = pickle.load(stream)

    def test_physical_symmetries(self):
        original = np.column_stack([feature_matrix(self.cases), structure_features(self.cases)])
        for kind in ('translation', 'reflection', 'inversion', 'uniform_offset'):
            cases = []
            for case in self.cases:
                fields = np.asarray(case['fields'])
                if kind == 'translation':
                    fields = np.roll(fields, 3)
                elif kind == 'reflection':
                    fields = fields[::-1]
                elif kind == 'inversion':
                    fields = -fields
                else:
                    fields = fields + 12.5
                cases.append(dict(case, fields=fields.tolist()))
            changed = np.column_stack([feature_matrix(cases), structure_features(cases)])
            np.testing.assert_allclose(original, changed, atol=1e-9, rtol=1e-9)
            np.testing.assert_allclose(predict_chunk(self.bundle, self.cases),
                                       predict_chunk(self.bundle, cases), atol=1e-6, rtol=1e-6)

    def test_quantile_transform(self):
        from sklearn.preprocessing import QuantileTransformer
        for component in self.bundle:
            features = assemble(self.cases, {component['model']['variant']})[component['model']['variant']]
            if component['kind'] == 'neural':
                transformer = component['model']['transformer']
                matrix = features
            else:
                model = component['model']['models'][0]
                transformer = model['transformer']
                matrix = features[:, model['columns']]
            reference = QuantileTransformer(output_distribution='normal')
            reference.quantiles_ = transformer.quantiles_
            reference.references_ = transformer.references_
            reference.n_quantiles_ = len(transformer.references_)
            reference.n_features_in_ = transformer.quantiles_.shape[1]
            np.testing.assert_allclose(transform(transformer, matrix),
                                       np.clip(reference.transform(matrix), -3, 3), atol=1e-12, rtol=1e-12)

    def test_native_features(self):
        expected = np.column_stack([feature_matrix(self.cases), structure_features(self.cases)])
        np.testing.assert_allclose(describe_cases(self.cases), expected, atol=1e-9, rtol=1e-9)
        columns = np.r_[0:226, 594:889]
        np.testing.assert_allclose(describe_cases(self.cases, spectral=False)[:, columns],
                                   expected[:, columns], atol=1e-9, rtol=1e-9)


if __name__ == '__main__':
    unittest.main()
