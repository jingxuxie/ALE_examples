import sys

import numpy as np
from scipy.special import logsumexp


def independent_rates(data):
    rates = np.zeros(int(data["n"]))
    for row, center in enumerate(data["centers"]):
        size = int(data["scope_size"][row])
        scope = list(data["scope_nodes"][row, :size])
        start, stop = data["local_ptr"][row:row + 2]
        indices = np.arange(stop - start)
        rates[center] = np.sum(data["local_probs"][start:stop][indices >> scope.index(center) & 1 == 1])
    return rates


def solve(data):
    rates = independent_rates(data)
    predictions = []
    for query, activity in enumerate(data["log_activity"]):
        logits = np.log(rates) - np.log1p(-rates) + activity
        log_one = -np.logaddexp(0.0, -logits)
        log_zero = -np.logaddexp(0.0, logits)
        upper = int(data["weight_hi"][query])
        states = np.full((upper + 1, 2), -np.inf)
        states[0, 0] = 0.0
        for node in range(int(data["n"])):
            updated = np.full_like(states, -np.inf)
            for value in (0, 1):
                if data["fixed"][query, node] not in (-1, value):
                    continue
                count = int(data["count_mask"][query, node]) * value
                if count > upper:
                    continue
                parity = int(data["parity_mask"][query, node]) * value if data["parity_value"][query] != -1 else 0
                contribution = states[:upper + 1 - count] + (log_one[node] if value else log_zero[node])
                if parity:
                    contribution = contribution[:, ::-1]
                np.logaddexp(updated[count:], contribution, out=updated[count:])
            states = updated
        lower = int(data["weight_lo"][query])
        parity = int(data["parity_value"][query])
        selected = states[lower:] if parity == -1 else states[lower:, parity]
        predictions.append(min(0.0, float(logsumexp(selected))))
    return np.asarray(predictions)


if __name__ == "__main__":
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = dict(archive)
    np.savez(sys.argv[2], log_event=solve(data))
