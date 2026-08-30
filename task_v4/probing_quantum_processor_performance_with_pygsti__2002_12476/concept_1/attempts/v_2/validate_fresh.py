from optimize import *
from physics import validate_batches
from concurrent.futures import ProcessPoolExecutor


def initialize(candidates, supports, counts):
    global LOCAL_CANDIDATES, LOCAL_SUPPORTS, LOCAL_COUNTS
    LOCAL_CANDIDATES = candidates
    LOCAL_SUPPORTS = supports
    LOCAL_COUNTS = counts


def evaluate(arguments):
    seed, family = arguments
    parameters = sample_parameters(np.random.default_rng(seed), family)
    features = fisher_features(parameters, LOCAL_CANDIDATES)
    intact = []
    loss = []
    for support, counts in zip(LOCAL_SUPPORTS, LOCAL_COUNTS):
        point_intact, point_loss = profile(features[None], support, counts)
        intact.append(point_intact[0])
        loss.append(point_loss[0])
    return parameters, features, intact, loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('designs', nargs='+')
    parser.add_argument('--count', type=int, default=512)
    parser.add_argument('--seed', type=int, default=51038181)
    parser.add_argument('--output', default='fresh_validation')
    args = parser.parse_args()
    contract = json.loads((ROOT / 'input/contract.json').read_text())
    designs = [BASELINE]
    names = ['champion']
    costs = []
    for filename in args.designs:
        batches, cost = validate_batches(json.loads(Path(filename).read_text())['batches'], CANDIDATES, contract)
        designs.append(batches)
        names.append(filename)
        costs.append(cost)
    union = np.flatnonzero(np.any(np.array(designs) > 0, axis=0))
    candidates = [CANDIDATES[index] for index in union]
    supports = [np.flatnonzero(batches[union]) for batches in designs]
    counts = [batches[batches > 0] for batches in designs]
    families = np.repeat(FAMILIES, args.count)
    arguments = [(args.seed + index, family) for index, family in enumerate(families)]
    started = time.time()
    with ProcessPoolExecutor(max_workers=4, initializer=initialize, initargs=(candidates, supports, counts)) as pool:
        results = list(pool.map(evaluate, arguments, chunksize=8))
    intact = np.array([result[2] for result in results])
    loss = np.array([result[3] for result in results])
    np.savez_compressed(args.output + '.npz', names=np.array(names), families=families,
                        union=union, parameters=np.array([result[0] for result in results]),
                        features=np.array([result[1] for result in results]),
                        intact=intact, loss=loss, batches=np.array(designs))
    report = {'operating_points': len(families), 'seed': args.seed, 'designs': {}}
    for design_index, name in enumerate(names[1:], 1):
        result = {'core_score': float(1 - loss[:, design_index].mean() / loss[:, 0].mean()),
                  'mean_loss_risk': float(loss[:, design_index].mean()),
                  'mean_intact_risk': float(intact[:, design_index].mean()),
                  'intact_mean_ratio': float(intact[:, design_index].mean() / intact[:, 0].mean()),
                  'execution_ticks': costs[design_index - 1], 'family_scores': {}}
        for family in FAMILIES:
            selected = families == family
            result['family_scores'][family] = float(1 - loss[selected, design_index].mean() / loss[selected, 0].mean())
        result['worst_family_score'] = min(result['family_scores'].values())
        result['passed'] = result['core_score'] >= .5 and result['worst_family_score'] >= .3 and result['intact_mean_ratio'] <= 1.2
        report['designs'][name] = result
    report['elapsed_seconds'] = time.time() - started
    Path(args.output + '.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
