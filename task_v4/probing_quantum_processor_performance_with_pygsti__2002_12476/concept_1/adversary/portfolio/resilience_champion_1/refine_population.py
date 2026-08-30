import argparse
import copy
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from rebased import HERE, profile, score_profiles, write_json
from optimize import RebasedSearch


class PopulationSearch(RebasedSearch):
    def __init__(self, seconds, per_family):
        super().__init__(seconds, 38741702)
        self.frozen = self.data
        self.data = copy.copy(self.frozen)
        with np.load(HERE / "broad_features.npz", allow_pickle=False) as source:
            self.broad_features = source["features"].copy()
            self.broad_families = source["families"].copy()
            self.broad_parameters = source["parameters"].copy()
            self.union = source["candidate_union"].copy()
        with np.load(HERE / "broad_profiles.npz", allow_pickle=False) as source:
            self.broad_reference = {mode: source["reference_" + mode + "_risks"].copy() for mode in ["intact", "single", "double"]}
        selected = np.concatenate([self.rng.choice(np.flatnonzero(self.broad_families == family), per_family, replace=False)
                                   for family in np.unique(self.broad_families)])
        training_features = np.zeros((len(selected), len(self.costs), 14))
        training_features[:, self.union] = self.broad_features[selected]
        self.data.features = np.concatenate([self.frozen.features, training_features])
        self.data.parameters = np.concatenate([self.frozen.parameters, self.broad_parameters[selected]])
        self.data.families = np.concatenate([np.array(["hidden/" + str(family) for family in self.frozen.families]),
                                             np.array(["broader/" + str(family) for family in self.broad_families[selected]])])
        self.data.reference = {mode: np.concatenate([self.frozen.reference[mode], self.broad_reference[mode][selected]])
                               for mode in ["intact", "single", "double"]}
        self.rows = self.data.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
        self.allowed_candidates = self.union.copy()
        self.dataset_masks = [np.arange(len(self.rows)) < len(self.frozen.features),
                              np.arange(len(self.rows)) >= len(self.frozen.features)]
        self.training_indices = selected
        np.savez_compressed(HERE / "population_training.npz", broad_indices=selected, candidate_union=self.union)
        self.log("population_refinement", training_points=len(selected), broad_selection_points=len(self.broad_families),
                 candidate_pool=len(self.union), fresh_draws_not_used=True)

    def log(self, event, **values):
        record = dict(elapsed_seconds=time.monotonic() - self.started, event=event, **values)
        with (HERE / "population_search.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        print(json.dumps(record, allow_nan=False), flush=True)

    def state(self, allocation, support, all_gradients=False):
        state = super().state(allocation, support, all_gradients)
        if not hasattr(self, "dataset_masks"):
            return state
        ratios = list(state[4])
        gradients = list(state[5])
        for mask in self.dataset_masks:
            normalizer = self.data.reference["double"][mask].mean()
            ratios.append(float(state[6][mask].mean() / normalizer * 0.7 / 0.5))
            gradients.append(state[7][mask].mean(axis=0) / normalizer * 0.7 / 0.5)
            intact_normalizer = self.data.reference["intact"][mask].mean()
            ratios.append(float(state[8][mask].mean() / intact_normalizer * 0.7 / 1.175))
            gradients.append(state[9][mask].mean(axis=0) / intact_normalizer * 0.7 / 1.175)
        return state[:4] + (np.array(ratios), np.array(gradients)) + state[6:]

    def consider(self, counts, label):
        self.evaluations += 1
        try:
            hidden = self.frozen.evaluate(counts, direct=True)
            broad_profile = profile(self.broad_features, counts[self.union], direct=False)
            broad = score_profiles(broad_profile, self.broad_reference, self.broad_families)
        except (ValueError, np.linalg.LinAlgError):
            return
        combined = dict(hidden=hidden, broad=broad,
                        intact_mean_ratio=max(hidden["intact_mean_ratio"], broad["intact_mean_ratio"]),
                        valid=True, execution_ticks=hidden["execution_ticks"], distinct_circuits=hidden["distinct_circuits"],
                        broad_used_for_selection=True, training_points=len(self.training_indices))
        combined["double"] = dict(core_score=min(hidden["double"]["core_score"], broad["double"]["core_score"]),
                                  worst_family_score=min(hidden["double"]["worst_family_score"], broad["double"]["worst_family_score"]),
                                  passed=hidden["double"]["passed"] and broad["double"]["passed"])
        if self.best["double"] is not None and self.key(combined, "double") >= self.key(self.best["double"], "double") - 1e-8:
            return
        broad = score_profiles(profile(self.broad_features, counts[self.union], direct=True), self.broad_reference, self.broad_families)
        combined["broad"] = broad
        self.best["double"] = combined
        self.best_counts["double"] = counts.copy()
        write_json(HERE / "robust_design.json", {"batches": counts.tolist()})
        write_json(HERE / "robust_score.json", combined)
        self.log("population_improvement", label=label, hidden_core=hidden["core_score"], hidden_worst=hidden["worst_family_score"],
                 broad_core=broad["double"]["core_score"], broad_worst=broad["double"]["worst_family_score"],
                 intact_max=combined["intact_mean_ratio"], passed=combined["double"]["passed"],
                 allocation={str(index): int(counts[index]) for index in np.flatnonzero(counts)})

    def run_population(self):
        counts = np.array(json.loads((HERE / "first_passing_design.json").read_text())["batches"])
        self.consider(counts, "first_passing_proof")
        self.exchange(counts, rounds=4, width=6)
        self.log("population_finished", seconds=time.monotonic() - self.started,
                 passed=self.best["double"]["double"]["passed"], evaluations=self.evaluations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=360)
    parser.add_argument("--per-family", type=int, default=50)
    args = parser.parse_args()
    PopulationSearch(args.seconds, args.per_family).run_population()


if __name__ == "__main__":
    main()
