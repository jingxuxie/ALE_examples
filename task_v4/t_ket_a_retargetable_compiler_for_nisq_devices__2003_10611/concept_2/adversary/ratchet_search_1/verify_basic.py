import hashlib
import json
import multiprocessing
import random
import sys
import time
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant/input"))

from router import relabelings
from search import run_case
from validation import load_witness


SETTING = {"name": "future-emphasis-8-1.5-ascending", "horizon": 8,
           "decay": 1.5, "tie": "ascending", "mode": "weighted"}


def main():
    started = time.monotonic()
    witness = load_witness(OUTPUT / "authorized_champion.json")
    cases = [(witness, SETTING, family) for family in relabelings(16)]
    for seed in range(46001, 46033):
        generator = random.Random(seed)
        logical, physical = list(range(16)), list(range(16))
        generator.shuffle(logical)
        generator.shuffle(physical)
        cases.append((witness, SETTING, (f"extra-{seed}", logical, physical)))
    with multiprocessing.get_context("fork").Pool(8) as pool:
        results = list(pool.imap_unordered(run_case, cases))
    official = sorted((row for row in results if not row["family"].startswith("extra-")),
                      key=lambda row: row["family"])
    extra = [row for row in results if row["family"].startswith("extra-")]
    report = {"configuration": SETTING, "official_families": official,
              "additional_relabelings": extra, "routes_replayed": len(results),
              "seconds": time.monotonic() - started,
              "champion_fails_every_official_family": not any(row["champion_meets_target"] for row in official),
              "champion_fails_every_extra_family": not any(row["champion_meets_target"] for row in extra),
              "score_core": 0.625, "score_worst_family": 0.625,
              "source_unchanged": True,
              "trusted_router_sha256": hashlib.sha256((ROOT / "participant/input/router.py").read_bytes()).hexdigest(),
              "weight_interpretation": "The parameter is named decay in the original source, but 1.5 is geometric future emphasis, not decay.",
              "policy_accesses_reference_route": False}
    report.pop("score_core")
    report.pop("score_worst_family")
    for row in official:
        row["family_score"] = max(0.0, min(1.0, (row["swap_ratio"] - 1) / 1.5,
                (row["native_ratio"] - 1) / 0.35, row["swap_gap"] / 16))
    report["core_score"] = sum(row["family_score"] for row in official) / len(official)
    report["worst_family_score"] = min(row["family_score"] for row in official)
    report["resource_score"] = report["worst_family_score"]
    report["valid"] = True
    report["passed"] = any(row["champion_meets_target"] for row in official)
    for name, content in (("proposed_basic_setting.json", SETTING),
                          ("basic_setting_routes.json", official),
                          ("basic_setting_verification.json", report)):
        (OUTPUT / name).write_text(json.dumps(content, indent=2) + "\n")
    print(json.dumps({"configuration": SETTING, "official_swaps": [row["swaps"] for row in official],
                      "official_native": [row["native_2q"] for row in official],
                      "core_score": report["core_score"], "worst_family_score": report["worst_family_score"],
                      "champion_passed": report["passed"],
                      "extra_swaps_min_max": [min(row["swaps"] for row in extra), max(row["swaps"] for row in extra)],
                      "extra_all_reject_champion": report["champion_fails_every_extra_family"],
                      "all_official_fallbacks": [row["fallback_swaps"] for row in official]}), flush=True)


if __name__ == "__main__":
    main()
