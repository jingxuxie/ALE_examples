from optimize import *
from physics import validate_batches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('designs', nargs='+')
    parser.add_argument('--data', default='validation.npz')
    args = parser.parse_args()
    data = np.load(args.data)
    features = data['features']
    families = data['families']
    base_intact, base_loss = profile(features, np.flatnonzero(BASELINE), BASELINE[BASELINE > 0])
    contract = json.loads((ROOT / 'input/contract.json').read_text())
    for filename in args.designs:
        batches, cost = validate_batches(json.loads(Path(filename).read_text())['batches'], CANDIDATES, contract)
        support = np.flatnonzero(batches)
        intact, loss = profile(features, support, batches[support])
        print('\nDESIGN', filename, 'cost', cost, 'support', len(support), flush=True)
        print('overall loss', loss.mean(), 'reduction', 1-loss.mean()/base_loss.mean(),
              'intact', intact.mean(), 'ratio', intact.mean()/base_intact.mean(), flush=True)
        for family in FAMILIES:
            selected = families == family
            relative = loss[selected] / base_loss[selected]
            print(family, 'loss', round(loss[selected].mean(), 5),
                  'reduction', round(1-loss[selected].mean()/base_loss[selected].mean(), 5),
                  'point_ratio_q', np.round(np.quantile(relative, [.5, .9, .99, 1]), 3),
                  'max_loss', round(loss[selected].max(), 4), flush=True)
        rng = np.random.default_rng(10003)
        for count in [3, 6, 12, 24]:
            sample_intact = []
            sample_base_intact = []
            sample_loss = []
            sample_base_loss = []
            family_ok = np.ones(5000, dtype=bool)
            for family in FAMILIES:
                selected = np.flatnonzero(families == family)
                indices = rng.choice(selected, size=(5000, count))
                mean_loss = loss[indices].mean(axis=1)
                mean_base_loss = base_loss[indices].mean(axis=1)
                family_ok &= mean_loss <= .7 * mean_base_loss
                sample_loss.append(mean_loss)
                sample_base_loss.append(mean_base_loss)
                sample_intact.append(intact[indices].mean(axis=1))
                sample_base_intact.append(base_intact[indices].mean(axis=1))
            intact_ok = np.mean(sample_intact, axis=0) <= 1.2 * np.mean(sample_base_intact, axis=0)
            loss_ok = np.mean(sample_loss, axis=0) <= .5 * np.mean(sample_base_loss, axis=0)
            print('bootstrap', count, 'pass', np.mean(intact_ok & loss_ok & family_ok),
                  'intact_fail', np.mean(~intact_ok), 'family_fail', np.mean(~family_ok), flush=True)


if __name__ == '__main__':
    main()
