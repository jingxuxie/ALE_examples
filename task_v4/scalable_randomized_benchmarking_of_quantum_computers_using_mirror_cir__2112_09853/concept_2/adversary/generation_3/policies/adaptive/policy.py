import json
import math
from pathlib import Path
import sys
import time

import numpy as np

from champion_policy import Policy, exchange


class BudgetPolicy(Policy):
    def run(self):
        settings = json.loads((Path(__file__).parent / "allocation.json").read_text())
        budget = self.hello["limits"]["shots_budget"]
        self.query([], 256, 64 if budget >= 3000 else 32)
        control_count = min(self.edge_count, max(1, round(self.edge_count * budget / 12000)))
        if settings["allocation"] == "adaptive":
            control_count = min(control_count, 2)
        for edge in self.generator.permutation(self.edge_count)[:control_count]:
            self.query([int(edge)], 192)
        initial = max(4, round((100 if settings["allocation"] == "adaptive" else 180) * budget / 12000))
        for index in range(initial):
            matching = self.random_matching()
            if index % 12 == 0 and self.used + 64 <= budget:
                self.query(matching, 0)
            if self.used + 32 > budget:
                break
            expected = .0025 + .0045 * len(matching)
            expected += self.features([matching])[0, self.edge_count + 1:] @ (self.prior * .0225)
            depth = int(2 * round(1.55 / expected / 2))
            self.query(matching, min(256, max(2, depth)))
        while (self.used + 32 <= budget and time.process_time() - self.cpu_started < 42
               and time.monotonic() - self.started < 66):
            self.fit()
            count = min(45, (budget - self.used) // 32)
            if self.family == 3 and count >= 10:
                for unused in range(4):
                    self.query(self.random_matching(), 0)
                count -= 4
            self.adaptive_batch(count)
        self.fit(1500, 500, 4)
        targets = self.exchange({"type": "ready"})["matchings"]
        rates = self.features(targets) @ self.samples[:, :self.rate_count].T
        values = -np.expm1(-rates)
        weights = 1 / (.003 + .1 * values) ** 2
        predictions = (values * weights).sum(axis=1) / weights.sum(axis=1)
        self.exchange({"type": "final", "predictions": predictions.tolist()})
        inclusion = np.mean(self.samples[:, self.edge_count + 1:self.rate_count] > 0, axis=0)
        print(json.dumps({"selected_pairs": self.pairs[inclusion > .5].tolist(),
                          "base": self.samples[:, 1:self.edge_count + 1].mean(axis=0).tolist(),
                          "posterior_inclusion": inclusion.tolist(),
                          "all_pairs": self.pairs.tolist()}), file=sys.stderr, flush=True)


if __name__ == "__main__":
    BudgetPolicy(json.loads(sys.stdin.readline()), exchange).run()
