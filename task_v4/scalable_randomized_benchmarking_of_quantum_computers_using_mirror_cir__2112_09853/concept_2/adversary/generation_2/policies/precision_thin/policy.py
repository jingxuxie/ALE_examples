import json
from pathlib import Path
import sys

import numpy as np

from champion_policy import Policy, exchange


class BudgetPolicy(Policy):
    def acquire(self):
        settings = json.loads((Path(__file__).parent / "allocation.json").read_text())
        budget = self.hello["limits"]["shots_budget"]
        pair_count = min(384, budget // settings["pair_shots_minimum"])
        pair_shots, remainder = divmod(budget, pair_count)
        midpoint = max(1, pair_count // 2)
        controls = [[]] + [[edge] for edge in self.generator.permutation(self.edge_count).tolist()] + [[]]
        if settings["thin_controls"]:
            control_count = min(len(controls), max(4, pair_count // 4))
            controls = controls[:control_count - 1] + [[]]
        for index in range(pair_count):
            if index == midpoint:
                self.fit()
            if index < len(controls):
                matching = controls[index]
            else:
                size = self.maximum if self.generator.random() < .85 else self.maximum - 2
                matching = None
                while matching is None:
                    forced = ()
                    if self.generator.random() < .8:
                        weights = 1. / (3. + self.pair_counts)
                        pair = self.generator.choice(len(self.pairs), p=weights / weights.sum())
                        forced = tuple(self.pairs[pair].tolist())
                    matching = self.matching(size, forced)
            row = self.features(matching)
            if index < midpoint:
                estimate = .0025 + .0045 * len(matching)
                estimate += .0225 * (round(.3 * self.edge_count) + .5) * row[self.offset:].sum() / len(self.pairs)
            else:
                estimate = max(.001, .01 * row @ self.beta)
            depth = int(np.clip(2 * round(1.5 / estimate / 2), 2, 256))
            allocated = pair_shots + int(index < remainder)
            reference_shots = max(32, min(allocated - 32, int(round(.1536 * allocated))))
            reference = self.exchange({"type": "experiment", "matching": matching, "depth": 0, "shots": reference_shots})
            decayed = self.exchange({"type": "experiment", "matching": matching, "depth": depth, "shots": allocated - reference_shots})
            self.records.append((row, depth, reference, decayed))
            self.pair_counts += row[self.offset:]
        self.fit(exact=True)


if __name__ == "__main__":
    hello = json.loads(sys.stdin.readline())
    agent = BudgetPolicy(hello, exchange)
    agent.run()
    selected = np.flatnonzero(agent.beta[agent.offset:] > .000001)
    print(json.dumps({"selected_pairs": agent.pairs[selected].tolist(),
                      "base": (.01 * agent.beta[1:agent.offset]).tolist(),
                      "pair_coefficients": (.01 * agent.beta[agent.offset:][selected]).tolist()}), file=sys.stderr, flush=True)
