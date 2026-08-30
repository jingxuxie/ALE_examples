import pickle
import time

import numpy as np
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import HistGradientBoostingRegressor

from neural import features


def main():
    data = np.load('train.npz')
    started = time.time()
    for order in [4, 5]:
        inputs, targets, scales, masks = features(data['energies'], data['orbitals'], data['families'], order)
        split = len(inputs) - 1800
        responses = np.log(np.maximum(np.abs(targets), 0.00001))
        model = HistGradientBoostingRegressor(max_iter=180, max_leaf_nodes=31, max_bins=63, l2_regularization=10, learning_rate=0.1, early_stopping=False)
        model.fit(inputs[:split].reshape(-1, inputs.shape[-1]), responses[:split].reshape(-1))
        predicted = np.exp(model.predict(inputs[split:].reshape(-1, inputs.shape[-1]))).reshape(-1, len(masks)) * scales[split:]
        with open('variance' + str(order) + '.pkl', 'wb') as handle:
            pickle.dump(model, handle)
        np.savez('variance_validation' + str(order) + '.npz', predicted=predicted, masks=masks)
        print(order, 'seconds', time.time() - started, flush=True)


if __name__ == '__main__':
    main()
