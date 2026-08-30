import sys

sys.dont_write_bytecode = True

import datetime
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess

import numpy as np

from cases import cases
from run import check_frozen


PREP = Path(__file__).resolve().parent
CONCEPT = PREP.parents[1]
PREVIOUS = CONCEPT / "generations/generation_2"
ROOT = CONCEPT / "generations/generation_3"


def add(relative, contents):
    patch = "*** Begin Patch\n*** Add File: " + str(ROOT / relative) + "\n"
    patch += "".join("+" + line + "\n" for line in contents.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)


def main():
    check_frozen()
    if ROOT.exists():
        raise RuntimeError("Do not overwrite an existing draft")
    for directory in ("participant/input", "participant/baseline", "participant/workspace", "evaluator/hidden",
                      "attempts", "champions", "adversary/portfolio", "adversary/validation"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    targets = json.loads((PREVIOUS / "participant/input/targets.json").read_text())
    targets.update({"generation": 3, "version": "connected-calibration-generation-3-draft", "draft": True,
                    "mean_family_log_rmse_max": 0.09, "worst_regime_family_log_rmse_max": 0.14,
                    "frozen_before_portfolio_and_fresh": False,
                    "proposal_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    targets.pop("precommit_sha256", None)
    for relative in ("participant/input/targets.json", "evaluator/hidden/targets.json"):
        (ROOT / relative).write_text(json.dumps(targets, indent=2) + "\n")
    proposal = {"targets": targets, "no_final_freeze": True, "main_selection_required": True,
                "rationale": "At 40k shots the larger nine-case uniform/local controls measured .1056/.1380 and .0792/.1188. Proposed .090/.140 keeps a meaningful allocation gap without asserting the older .075 mean is attainable. Independently resampled draft fixtures must qualify; no fresh participant or final seal is authorized yet."}
    (ROOT / "adversary/target_proposal.json").write_text(json.dumps(proposal, indent=2) + "\n")
    seeds = {}
    for split in ("private", "training"):
        seeds[split] = {name: secrets.randbits(128) for name in ("graph", "rates")}
        rate_rng = np.random.default_rng(seeds[split]["rates"])
        episodes = list(cases(seed=seeds[split]["graph"], sizes=(28, 32, 36, 44) if split == "private" else (28, 44)))
        for episode in episodes:
            bounds = np.log([channel["rate_bounds"] for channel in episode["spec"]["channels"]])
            episode["rates"] = np.exp(rate_rng.uniform(bounds[:, 0], bounds[:, 1])).tolist()
            episode["sample_seed"] = secrets.randbits(63)
            episode["spec"]["protocol"] = "connected-detector-calibration-v3"
            episode["id"] = split + "_" + episode["id"]
        relative = "evaluator/hidden/episodes.json" if split == "private" else "participant/input/training.json"
        (ROOT / relative).write_text(json.dumps({"episodes": episodes}, indent=2) + "\n")
    (ROOT / "evaluator/hidden/generation_seeds.json").write_text(json.dumps(seeds, indent=2) + "\n")
    for relative in ("participant/input/simulator.py", "participant/input/moments.py", "participant/input/local.py",
                     "participant/baseline/solution.py", "participant/workspace/README.md", "evaluator/evaluate.py",
                     "evaluator/hidden/simulator.py", "evaluator/hidden/worker_supervisor.py",
                     "evaluator/hidden/case_factory.py", "adversary/science_helpers.py", "adversary/validation_model.py"):
        add(relative, (PREVIOUS / relative).read_text())
    task = (PREVIOUS / "participant/TASK.md").read_text()
    task = task.replace("# Efficient active detector calibration", "# DRAFT: Connected active detector calibration")
    task = task.replace("14–20", "28–44").replace("43–77", "88–179").replace("0.075", "0.090").replace("0.125", "0.140")
    task = task.replace("These targets were fixed before generation-two policy trials and fresh runs.",
                        "These criteria are proposed before draft qualification; main must authorize final sealing before any fresh run.")
    task = task.replace("`baseline/previous_champion.py`", "`baseline/previous_champion/solution.py`")
    add("participant/TASK.md", task)
    api = (PREVIOUS / "participant/input/API.md").read_text()
    api = api.replace("efficient-detector-calibration-v2", "connected-detector-calibration-v3")
    api = api.replace("between 14 and 20", "between 28 and 44")
    start = api.index("To test the supplied historical policy")
    end = api.index("## Scientific scope", start)
    api = api[:start] + '''To test the supplied historical policy, run from the participant directory
with `ATTEMPT_DIR` set to the launcher-provided writable directory. Copy the
complete `baseline/previous_champion/` directory into your writable directory
if you want to modify or preserve its supporting assets. The original program
can also be tested directly:

```
/usr/bin/python3 input/local.py --episode 0 --workdir "$ATTEMPT_DIR" --output "$ATTEMPT_DIR/reference_report.json" -- /usr/bin/python3 "$PWD/baseline/previous_champion/solution.py"
```

The reference already uses this sparse observation format. Both reference
programs are optional starting points, not promised passing solutions.
Syndrome codes and footprint masks may require more than 32 bits; their exact
integer values, not a truncated machine-word representation, define the API.

''' + api[end:]
    add("participant/input/API.md", api)
    shutil.copytree(PREP / "actual_champion_snapshot", ROOT / "participant/baseline/previous_champion")
    (ROOT / "adversary/provisional_champion_manifest.json").write_bytes((PREP / "actual_champion_manifest.json").read_bytes())
    add("adversary/portfolio/local_model.py", (PREP / "worker_support/local_model.py").read_text())
    policy = (PREP / "workers/reference/solution.py").read_text().replace('sys.path.insert(0, "/stress_public")',
                   'sys.path.insert(0, str(Path(__file__).resolve().parent))')
    add("adversary/portfolio/solution.py", policy)
    hashes = {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
              for relative in ("evaluator/hidden/targets.json", "evaluator/hidden/episodes.json")}
    (ROOT / "adversary/draft_snapshot.json").write_text(json.dumps({"files": hashes, "not_a_final_freeze": True}, indent=2) + "\n")
    (ROOT / "status.json").write_text(json.dumps({"generation": 3, "status": "draft_selection_pending",
        "frozen": False, "fresh_launches": 0, "main_must_confirm_best_champion": True,
        "target_proposal": {"mean": 0.09, "worst": 0.14}}, indent=2) + "\n")
    check_frozen()
    print("Draft generation three created. No freeze.json or launch authorization exists.", flush=True)


if __name__ == "__main__":
    main()
