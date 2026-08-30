import argparse
import copy
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import HERE, TARGETS, profile, score_profiles
from search import Search


class Refine(Search):
    def __init__(self, seconds, per_family):
        super().__init__(seconds, 977001)
        self.frozen = self.data
        self.data = copy.copy(self.frozen)
        with np.load(HERE / "broad_features.npz", allow_pickle=False) as data:
            self.broad_features = data["features"].copy()
            self.broad_families = data["families"].copy()
            self.broad_parameters = data["parameters"].copy()
            self.union = data["candidate_union"].copy()
        with np.load(HERE / "broad_profiles.npz", allow_pickle=False) as data:
            self.broad_reference = {mode: data["reference_" + mode + "_risks"].copy() for mode in ["intact", "single", "double"]}
        rng = np.random.default_rng(772411)
        selected = np.concatenate([rng.choice(np.flatnonzero(self.broad_families == family), per_family, replace=False)
                                   for family in np.unique(self.broad_families)])
        training_features = np.zeros((len(selected), len(self.costs), 14))
        training_features[:, self.union] = self.broad_features[selected]
        self.data.features = np.concatenate([self.frozen.features, training_features])
        self.data.families = np.concatenate([np.array(["hidden/" + str(family) for family in self.frozen.families]),
                                             np.array(["broader/" + str(family) for family in self.broad_families[selected]])])
        self.data.parameters = np.concatenate([self.frozen.parameters, self.broad_parameters[selected]])
        extra_reference = profile(training_features, self.frozen.reference_counts, direct=True)
        self.data.reference = {mode: np.concatenate([self.frozen.reference[mode], extra_reference[mode]])
                               for mode in ["intact", "single", "double"]}
        self.rows = self.data.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
        self.allowed_candidates = self.union.copy()
        self.dataset_masks = [np.arange(len(self.rows)) < len(self.frozen.features),
                              np.arange(len(self.rows)) >= len(self.frozen.features)]
        self.temperature_ratio = 0.0025
        self.training_indices = selected
        np.savez_compressed(HERE / "refinement_training.npz", broad_indices=selected, candidate_union=self.union)
        self.log("broader_refinement", training_points=len(selected), hidden_points=len(self.frozen.features),
                 candidate_pool=len(self.union), broad_points_used_for_selection=True)

    def log(self, event, **values):
        result = dict(elapsed_seconds=time.monotonic() - self.started, event=event, **values)
        with (HERE / "refinement.jsonl").open("a") as stream:
            stream.write(json.dumps(result, allow_nan=False) + "\n")
        print(json.dumps(result, allow_nan=False), flush=True)

    def state(self, allocation, support, all_gradients=False):
        base = super().state(allocation, support, all_gradients)
        if not hasattr(self, "dataset_masks"):
            return base
        ratios = list(base[4])
        gradients = list(base[5])
        family_limit = 1 - TARGETS[self.mode + "_family_reduction"]
        core_limit = 1 - TARGETS[self.mode + "_core_reduction"]
        for mask in self.dataset_masks:
            normalizer = self.data.reference[self.mode][mask].mean()
            ratios.append(float(base[6][mask].mean() / normalizer * family_limit / core_limit))
            gradients.append(base[7][mask].mean(axis=0) / normalizer * family_limit / core_limit)
            intact_normalizer = self.data.reference["intact"][mask].mean()
            ratios.append(float(base[8][mask].mean() / intact_normalizer * family_limit / 1.187))
            gradients.append(base[9][mask].mean(axis=0) / intact_normalizer * family_limit / 1.187)
        return base[:4] + (np.array(ratios), np.array(gradients)) + base[6:]

    def consider(self, counts, label):
        self.evaluations += 1
        try:
            hidden = self.frozen.evaluate(counts, direct=True)
            broad_profile = profile(self.broad_features, counts[self.union], direct=False)
            broad = score_profiles(broad_profile, self.broad_reference, self.broad_families)
        except (ValueError, np.linalg.LinAlgError):
            return
        combined = dict(hidden=hidden, broad=broad, intact_mean_ratio=max(hidden["intact_mean_ratio"], broad["intact_mean_ratio"]),
                        valid=True, execution_ticks=hidden["execution_ticks"], distinct_circuits=hidden["distinct_circuits"],
                        broad_used_for_selection=True, broader_training_points=len(self.training_indices))
        for mode in ["single", "double"]:
            families = {"hidden/" + family: value for family, value in hidden[mode]["family_scores"].items()}
            families.update({"broad/" + family: value for family, value in broad[mode]["family_scores"].items()})
            combined[mode] = dict(core_score=min(hidden[mode]["core_score"], broad[mode]["core_score"]),
                                  worst_family_score=min(hidden[mode]["worst_family_score"], broad[mode]["worst_family_score"]),
                                  family_scores=families, passed=hidden[mode]["passed"] and broad[mode]["passed"])
        for mode in ["single", "double"]:
            if self.best[mode] is None or self.key(combined, mode) < self.key(self.best[mode], mode) - 1e-7:
                self.best[mode] = combined
                self.best_counts[mode] = counts.copy()
                (HERE / f"robust_{mode}.json").write_text(json.dumps({"batches": counts.tolist()}) + "\n")
                (HERE / f"robust_{mode}_score.json").write_text(json.dumps(combined, indent=2) + "\n")
                self.log("robust_improvement", mode=mode, label=label,
                         hidden_core=hidden[mode]["core_score"], hidden_worst=hidden[mode]["worst_family_score"],
                         broad_core=broad[mode]["core_score"], broad_worst=broad[mode]["worst_family_score"],
                         maximum_intact_ratio=combined["intact_mean_ratio"], passed=combined[mode]["passed"],
                         allocation={str(index): int(counts[index]) for index in np.flatnonzero(counts)})

    def run_refinement(self):
        self.consider(self.frozen.reference_counts, "reference")
        for mode in ["single", "double"]:
            counts = np.array(json.loads((HERE / f"best_{mode}.json").read_text())["batches"])
            self.consider(counts, "frozen_feasible_start")
        deadline = self.deadline
        for mode in ["single", "double"]:
            self.mode = mode
            self.family_boost = None
            self.deadline = min(deadline, time.monotonic() + (150 if mode == "single" else 180))
            self.exchange(self.best_counts[mode], rounds=4, width=6)
            if time.monotonic() >= deadline:
                break
        summary = dict(single_feasible_on_hidden_and_broad=self.best["single"]["single"]["passed"],
                       double_feasible_on_hidden_and_broad=self.best["double"]["double"]["passed"],
                       single=self.best["single"], double=self.best["double"],
                       seconds=time.monotonic() - self.started, training_points=len(self.training_indices),
                       broad_used_for_selection=True, original_design_and_audits_unchanged=True,
                       fresh_attempts_read=False, candidate_pool=self.union.tolist())
        (HERE / "refinement_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        self.log("refinement_complete", single_feasible=summary["single_feasible_on_hidden_and_broad"],
                 double_feasible=summary["double_feasible_on_hidden_and_broad"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=330)
    parser.add_argument("--per-family", type=int, default=30)
    args = parser.parse_args()
    Refine(args.seconds, args.per_family).run_refinement()


if __name__ == "__main__":
    main()
