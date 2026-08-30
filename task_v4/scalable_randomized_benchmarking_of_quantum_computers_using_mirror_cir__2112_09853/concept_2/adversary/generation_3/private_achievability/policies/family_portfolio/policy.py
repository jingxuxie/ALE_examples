import json
from pathlib import Path
import sys
import time

import numpy as np

from champion_policy import Policy, exchange


class PrivatePolicy(Policy):
    def run(self):
        settings = json.loads((Path(__file__).parent / "settings.json").read_text())
        budget = self.hello["limits"]["shots_budget"]
        self.query([], 256)
        for edge in self.generator.permutation(self.edge_count)[:settings["controls"]]:
            self.query([int(edge)], 192)
        for index in range(settings["initial"]):
            matching = self.random_matching()
            if index % 12 == 0 and self.used + 64 <= budget:
                self.query(matching, 0)
            if self.used + 32 > budget:
                break
            expected = .0025 + .0045 * len(matching)
            expected += self.features([matching])[0, self.edge_count + 1:] @ (self.prior * .0225)
            depth = int(2 * round(1.55 / expected / 2))
            self.query(matching, min(256, max(2, depth)))
        iteration = 0
        while (self.used + 32 <= budget and time.process_time() - self.cpu_started < 42
               and time.monotonic() - self.started < 66):
            self.fit(settings["sweeps"], settings["sweeps"] // 3, 5)
            count = min(settings["batch"], (budget - self.used) // 32)
            if self.family == 3 and iteration % 2 == 0 and count >= 3:
                self.query(self.random_matching(), 0)
                count -= 1
            self.adaptive_batch(count)
            iteration += 1
        self.fit(settings["final"], settings["final"] // 3, 10)
        targets = self.exchange({"type": "ready"})["matchings"]
        rates = self.features(targets) @ self.samples[:, :self.rate_count].T
        values = -np.expm1(-rates)
        weights = 1 / (.003 + .1 * values) ** 2
        predictions = (values * weights).sum(axis=1) / weights.sum(axis=1)
        self.exchange({"type": "final", "predictions": predictions.tolist()})
        inclusion = np.mean(self.samples[:, self.edge_count + 1:self.rate_count] > 0, axis=0)
        print(json.dumps({"posterior_support_count": float(inclusion.sum()),
                          "queries": len(self.rows), "shots_used": self.used,
                          "posterior_inclusion": inclusion.tolist(),
                          "all_pairs": self.pairs.tolist()}), file=sys.stderr, flush=True)


if __name__ == "__main__":
    PrivatePolicy(json.loads(sys.stdin.readline()), exchange).run()
