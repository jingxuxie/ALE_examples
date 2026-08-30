import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from cases import cases
from run import check_frozen, run_case


ROOT = Path(__file__).resolve().parent


def main():
    check_frozen()
    original = ROOT / "actual_champion_snapshot"
    results = []
    for case in cases(seed=49371023, sizes=(28, 44), topologies=("ladder", "triangular")):
        case["spec"]["protocol"] = "efficient-detector-calibration-v2"
        leaf = ROOT / "candidates/diagnostic_repair" / case["id"] / "submission"
        shutil.copytree(original, leaf)
        patch = "*** Begin Patch\n*** Update File: " + str(leaf / "solution.py") + '''
@@
-        self.original_masks = np.asarray([channel['masks'] for channel in spec['channels']], dtype=np.int32)
+        self.original_masks = np.asarray([channel['masks'] for channel in spec['channels']], dtype=np.int64)
@@
-        syndromes = np.zeros(samples, dtype=np.int32)
+        syndromes = np.zeros(samples, dtype=np.int64)
@@
-    full = Model(spec, size=spec['detector_count'])
-    for action, syndromes, counts in records:
-        full.add(action, syndromes, counts)
-    fitted = full.fit(fitted, np.sqrt(np.diag(covariance)), maxiter=30, deadline=51)
-    gradient = full.fitted_gradient
+    gradient = model.fitted_gradient
@@
-        return np.asarray(response['syndromes'], dtype=np.int32), np.asarray(response['multiplicities'], dtype=float)
+        return np.asarray(response['syndromes'], dtype=np.int64), np.asarray(response['multiplicities'], dtype=float)
*** End Patch
'''
        subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)
        logs = ROOT / "runs/diagnostic_repair_logs"
        logs.mkdir(parents=True, exist_ok=True)
        result = run_case(case, leaf, ["/usr/bin/python3", "/submission/solution.py"], logs)
        result["modified_diagnostic_only_not_actual_champion"] = True
        result["modified_source_sha256"] = hashlib.sha256((leaf / "solution.py").read_bytes()).hexdigest()
        results.append(result)
        (ROOT / "runs/diagnostic_repair.json").write_text(json.dumps({"cases": results, "targets": None,
            "qualification": "Width-only changes plus replacing the terminal full-state refit with the last local gradient. This is an explanatory ablation, not the original champion's result or a new official solution."}, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
