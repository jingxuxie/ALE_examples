from optimize import *
from physics import validate_batches
from resilience import risk_profile
import subprocess


def main():
    data = np.load('final_candidates.npz')
    names = data['names']
    designs = data['batches']
    families = data['families']
    choices = []
    for index in range(1, len(names)):
        batches = designs[index]
        support = np.flatnonzero(batches)
        intact, loss = profile(DATA['features'], support, batches[support])
        dev_family = [1 - loss[DATA['families'] == family].mean() / DATA['champion_loss_risks'][DATA['families'] == family].mean() for family in FAMILIES]
        dev_ratio = intact.mean() / DATA['champion_intact_risks'].mean()
        sampled_family = [1 - data['loss'][families == family, index].mean() / data['loss'][families == family, 0].mean() for family in FAMILIES]
        sampled_ratio = data['intact'][:, index].mean() / data['intact'][:, 0].mean()
        if min(dev_family) >= .3 and dev_ratio <= 1.2 and min(sampled_family) >= .3 and sampled_ratio <= 1.2:
            choices.append((data['loss'][:, index].mean(), index))
    if not choices:
        raise RuntimeError('No candidate passed validation')
    unused, selected = min(choices)
    batches = designs[selected]
    save(np.flatnonzero(batches), batches[batches > 0], 'design.json')
    submitted = json.loads(Path('design.json').read_text())
    assert set(submitted) == {'batches'} and not Path('design.json').is_symlink()
    batches, cost = validate_batches(submitted['batches'], CANDIDATES, json.loads((ROOT / 'input/contract.json').read_text()))
    public = subprocess.run([sys.executable, str(ROOT / 'workspace/check.py'), 'design.json'], check=True, text=True, capture_output=True)
    development = json.loads(public.stdout)
    print('selected', names[selected], development, flush=True)
    features = data['features']
    union = data['union']
    baseline_intact, baseline_loss, unused = risk_profile(features, BASELINE[union], 2, 64)
    intact, loss, unused = risk_profile(features, batches[union], 2, 64)
    family_scores = {family: float(1 - loss[families == family].mean() / baseline_loss[families == family].mean()) for family in FAMILIES}
    sampled = {'operating_points': len(features), 'points_per_regime': len(features) // 6,
               'core_score': float(1-loss.mean()/baseline_loss.mean()), 'family_scores': family_scores,
               'worst_family_score': min(family_scores.values()), 'mean_loss_risk': float(loss.mean()),
               'mean_intact_risk': float(intact.mean()), 'intact_mean_ratio': float(intact.mean()/baseline_intact.mean()),
               'execution_ticks': cost, 'all_loss_pairs_enumerated': True}
    sampled['passed'] = sampled['core_score'] >= .5 and sampled['worst_family_score'] >= .3 and sampled['intact_mean_ratio'] <= 1.2
    nominal_intact, nominal_loss, unused = risk_profile(DATA['nominal_features'][None], batches, 2, 64)
    report = {'development': development, 'sampled_validation': sampled,
              'selected_candidate': str(names[selected]), 'distinct_circuits': int(np.count_nonzero(batches)),
              'maximum_batches': int(batches.max()), 'total_shots': int(64*batches.sum()),
              'nominal_intact_risk': float(nominal_intact[0]), 'nominal_loss_risk': float(nominal_loss[0]),
              'fast_vs_direct_max_relative_error': float(np.max(abs(loss-data['loss'][:, selected])/loss))}
    assert development['passed'] and sampled['passed']
    Path('validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
