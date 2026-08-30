import json
from pathlib import Path
import sys
import time

import numpy as np

from champion_policy import Policy, exchange


class PrivatePolicy(Policy):
    def adaptive_batch(self, count):
        if not self.settings.get("probability_design"):
            return super().adaptive_batch(count)
        candidates = [self.random_matching() for unused in range(350)]
        candidates.extend(pair.tolist() for pair in self.pairs)
        for unused in range(100):
            candidates.append(self.random_matching(int(self.generator.integers(3, self.maximum))))
        features = self.features(candidates)
        rates = features @ self.samples[:, :self.rate_count].T
        base_depths = np.clip(2 * np.round(1.55 / rates.mean(axis=1) / 2), 2, 256)
        depth_options = np.clip(2 * np.round(base_depths[:, None] * np.array([.5, 1., 1.6])[None, :] / 2), 2, 256)
        context = (self.used + 16) / self.hello["limits"]["shots_budget"]
        spam = self.spam_features(candidates, np.full(len(candidates), context)) @ self.samples[:, self.rate_count:].T
        amplitudes = .58 + .37 / (1 + np.exp(-spam))
        probabilities = amplitudes[:, None, :] * np.exp(-depth_options[:, :, None] * rates[:, None, :])
        probabilities = probabilities.reshape(-1, rates.shape[1])
        centered = (probabilities - probabilities.mean(axis=1)[:, None]) / np.sqrt(rates.shape[1] - 1)
        noise = (probabilities * (1 - probabilities)).mean(axis=1) / 32
        goals = [self.random_matching(self.maximum + 1) for unused in range(250)]
        goal_values = -np.expm1(-(self.features(goals) @ self.samples[:, :self.rate_count].T))
        goal_centered = (goal_values - goal_values.mean(axis=1)[:, None]) / np.sqrt(rates.shape[1] - 1)
        goal_centered /= (.003 + .1 * goal_values.mean(axis=1))[:, None]
        importance = goal_centered.T @ goal_centered / len(goals)
        covariance = np.eye(rates.shape[1])
        for unused in range(count):
            projected = centered @ covariance
            variance = np.sum(projected * centered, axis=1)
            scores = np.sum((projected @ importance) * projected, axis=1) / (variance + noise)
            chosen = int(np.argmax(scores))
            direction = projected[chosen]
            covariance -= np.outer(direction, direction) / (variance[chosen] + noise[chosen])
            matching_index, depth_index = divmod(chosen, 3)
            self.query(candidates[matching_index], int(depth_options[matching_index, depth_index]))

    def run(self):
        settings = json.loads((Path(__file__).parent / "settings.json").read_text())
        self.settings = settings
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
