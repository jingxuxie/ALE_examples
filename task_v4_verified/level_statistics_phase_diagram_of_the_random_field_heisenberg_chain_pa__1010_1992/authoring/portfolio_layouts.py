import json
from pathlib import Path

import numpy as np


def main():
    root = Path(__file__).resolve().parents[1] / "concept_2"
    bank = "bank_2"
    cache = {}
    origins = {}
    def include(design, result, source):
        layout = next(record for record in design["layouts"] if record["id"] == bank)
        families = [record for record in result["families"] if record["bank"] == bank]
        for orientation in ("high", "low"):
            order = tuple(layout[orientation])
            values = np.array([[[row["r_" + orientation], row["f_" + orientation]]
                                for row in family["records"]] for family in families])
            if order in cache:
                assert np.max(np.abs(values - cache[order])) < 1e-9
            cache[order] = values
            origins.setdefault(order, source)
    for line in (root / "adversary/robust_pairs.jsonl").read_text().splitlines():
        record = json.loads(line)
        if record["bank_index"] == 1:
            include(record["design"], record["result"], "private_robust_pair_cache")
    sources = {"private_initial": (root / "adversary/privileged_candidate/design.json", root / "adversary/privileged_score.json")}
    for index in (1, 2):
        sources["fresh_" + str(index)] = (root / f"attempts/v_{index}/design.json", root / f"attempts/v_{index}.score.json")
    for identity, (design_path, score_path) in sources.items():
        include(json.loads(design_path.read_text()), json.loads(score_path.read_text()), identity)
    orders = list(cache)
    observations = np.array([cache[order] for order in orders])
    best = None
    passing = 0
    for high_index, high in enumerate(orders):
        ratio_difference = np.abs(observations[high_index, :, :, 0] - observations[:, :, :, 0])
        fraction_difference = observations[high_index, :, :, 1] - observations[:, :, :, 1]
        margins = np.minimum.reduce([0.02 / np.maximum(ratio_difference.mean(axis=2), 1e-15),
                                     0.045 / np.maximum(ratio_difference.max(axis=2), 1e-15),
                                     fraction_difference.mean(axis=2) / 0.28,
                                     fraction_difference.min(axis=2) / 0.24])
        worst = margins.min(axis=1)
        passing += int(np.count_nonzero(worst >= 1))
        low_index = int(np.argmax(worst))
        if best is None or worst[low_index] > best[0]:
            best = float(worst[low_index]), high_index, low_index
    maximum, high_index, low_index = best
    replacements = {bank: {"id": bank, "high": list(orders[high_index]), "low": list(orders[low_index])}}
    source_choices = {}
    for identity, (design_path, score_path) in sources.items():
        design = json.loads(design_path.read_text())
        score = json.loads(score_path.read_text())
        for layout in design["layouts"]:
            identity_bank = layout["id"]
            if identity_bank == bank:
                continue
            metric = min(row["score"] for row in score["families"] if row["bank"] == identity_bank)
            if identity_bank not in source_choices or metric > source_choices[identity_bank][0]:
                replacements[identity_bank] = layout
                source_choices[identity_bank] = metric, identity
    destination = root / "adversary/portfolio_candidate"
    destination.mkdir(exist_ok=True)
    (destination / "design.json").write_text(json.dumps({"layouts": [replacements[key] for key in sorted(replacements)]}, indent=2) + "\n")
    report = {"cache_layouts": len(orders), "ordered_pairs_checked": len(orders) ** 2,
              "passing_bank2_pairs": passing, "best_bank2_margin": maximum,
              "bank2_high_source": origins[orders[high_index]], "bank2_low_source": origins[orders[low_index]],
              "other_bank_sources": source_choices,
              "scope": "Privileged recombination of independently cached hidden responses; official full-design evaluation required"}
    (root / "adversary/portfolio_search.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
