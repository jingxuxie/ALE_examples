import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent


def main():
    required = ['workspace', 'run.sh', 'config.json', 'ablation_config.json', 'refinement_config.json',
                'results.csv', 'ablation.csv', 'scaling.csv', 'experiments/primary', 'experiments/ablation',
                'experiments/refinement', 'figures/primary_result.png', 'figures/robustness_or_scaling.png',
                'claims.json', 'report.md']
    for name in required:
        assert (ROOT / name).exists(), name
    for name in ['results.csv', 'ablation.csv', 'refinement.csv', 'scaling.csv', 'convergence.csv',
                 'independent_solver.csv', 'higher_refinement.csv']:
        records = list(csv.DictReader((ROOT / name).open()))
        assert records, name
        for record in records:
            for column, value in record.items():
                if column not in ('case', 'variant'):
                    assert math.isfinite(float(value)), (name, column, value)
    claims = json.loads((ROOT / 'claims.json').read_text())
    for claim in claims:
        assert all(name in claim for name in ('id', 'statement', 'evidence', 'comparison', 'value'))
        cited = []
        for reference in claim['evidence']:
            records = list(csv.DictReader((ROOT / reference['table']).open()))
            matching = [record for record in records if record['case'] == reference['case']
                        and int(record['frame']) == reference['frame']]
            assert len(matching) == 1, reference
            cited.append(float(matching[0][reference['column']]))
        expected = cited[0] - cited[1] if claim['comparison'] == 'difference' else cited[0] / cited[1]
        assert expected == claim['value'], (claim['id'], expected, claim['value'])
    campaign = json.loads((ROOT / 'inputs/campaign.json').read_text())
    checked_frames = 0
    for variant, config_file, summary in [('primary', 'config.json', 'results.csv'),
                                           ('ablation', 'ablation_config.json', 'ablation.csv'),
                                           ('refinement', 'refinement_config.json', 'refinement.csv')]:
        directory = ROOT / 'experiments' / variant
        assert json.loads((directory / 'configuration.json').read_text()) == json.loads((ROOT / config_file).read_text())
        assert (directory / 'results.csv').read_bytes() == (ROOT / summary).read_bytes()
        for case in campaign['cases']:
            with np.load(directory / (case['id'] + '.npz')) as saved:
                assert saved['psi'].dtype == np.complex128
                assert saved['psi'].shape[0] == len(case['times'])
                assert np.isfinite(saved['psi']).all()
                np.testing.assert_array_equal(saved['times'], case['times'])
            diagnostics = json.loads((directory / (case['id'] + '.json')).read_text())
            assert len(diagnostics) == len(case['times'])
            for frame in diagnostics:
                assert set(frame) == {'cores', 'topology', 'physics'}
                assert len(frame['topology']['counts']) == 13
                assert len(frame['topology']['correlations']) == len(case['correlation_edges']) - 1
                assert len(frame['physics']['Ec_bins']) == len(case['spectrum_edges']) - 1
            checked_frames += len(diagnostics)
    provenance = json.loads((ROOT / 'provenance.json').read_text())
    for name, digest in provenance['sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert json.loads((ROOT / 'experiments/smoke result/configuration.json').read_text()) == json.loads((ROOT / 'config.json').read_text())
    results = dict(status='passed', required_paths=len(required), checked_campaign_frames=checked_frames,
                   validated_claims=len(claims), source_and_input_hashes=len(provenance['sha256']),
                   default_configuration_smoke_test=True)
    (ROOT / 'handoff_validation.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
