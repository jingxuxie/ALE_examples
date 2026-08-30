import argparse
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('prefix')
args = parser.parse_args()
totals = np.zeros((6, 3))
for path in sorted(Path('.').glob(args.prefix + '_*.npz')):
    data = np.load(path)
    stats = data['stats']
    truth = data['labels'] @ np.array([1,2,4,8])
    scores = stats[:, :, :16]
    choices = scores.argmax(axis=2)
    ordered = np.sort(scores, axis=2)
    gaps = ordered[:,:,-1] - ordered[:,:,-2]
    print(path.stem, 'full', int((choices[:,-1]!=truth).sum()), 'gaps', np.percentile(gaps[:,1], [10,25,50,75,90]).round(2))
    for row, threshold in enumerate([2,3,4,5,6,8]):
        stop = np.full(len(truth), stats.shape[1] - 1, dtype=int)
        for trial in range(stats.shape[1]-2, 0, -1):
            confident = (gaps[:,trial] > threshold) & (choices[:,trial] == choices[:,trial-1])
            stop[confident] = trial
        stop[stats[:,0,32] > 0] = 0
        predictions = choices[np.arange(len(truth)), stop]
        bad = int((predictions != truth).sum())
        totals[row] += [bad, stop.sum()+len(stop), len(stop)]
        print(threshold, 'fail', bad, 'trials', round(stop.mean()+1,2), end='; ')
    print()
print('TOTAL')
for threshold, values in zip([2,3,4,5,6,8],totals):
    print(threshold, values[0], values[1]/max(values[2],1))
