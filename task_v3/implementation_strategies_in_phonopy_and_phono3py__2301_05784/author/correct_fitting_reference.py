"""Archive-preserving correction of the rank-deficient Si joint-fit target."""

import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


AUTHOR = Path(__file__).resolve().parent
PRIVATE = AUTHOR.parent / "concepts/fitting/private"
sys.path.insert(0, str(PRIVATE / "reference"))
from physics import error_metrics


manifest = json.loads((PRIVATE / "challenge_pool/manifest.json").read_text())
corrected_manifest = copy.deepcopy(manifest)
case = next(item for item in corrected_manifest if item["id"] == "initial_si_8")
reference = dict(np.load(PRIVATE / case["reference"], allow_pickle=False))
explicit = dict(np.load(AUTHOR / "si_audit/explicit_runtime.npz", allow_pickle=False))
reference.update(explicit)
destination = PRIVATE / "reference/validated_initial_si_8.npz"
np.savez_compressed(destination, **reference)
case["original_reference"] = case["reference"]
case["reference"] = str(destination.relative_to(PRIVATE))
case["files"]["reference"] = case["reference"]
case["reference_sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
data = dict(np.load(PRIVATE / case["input"], allow_pickle=False))
baseline = dict(np.load(PRIVATE / case["baseline"], allow_pickle=False))
case["baseline_metrics"] = error_metrics(baseline, reference, data)
case["oracle_correction"] = {
    "reason": "The 2304x17 joint design has rank16. The high-level normal-equation result violates the public least-squares objective; explicit SVD in the independently computed official invariant basis satisfies it.",
    "privileged_artifact": "symfc 1.5.4 invariant basis, cross-checked with symfc1.7.3",
    "diagnostic": "author/si_audit/runtime.json and runtime4.json",
    "participant_code_or_inputs_changed": False,
}
manifest_path = PRIVATE / "challenge_pool/manifest_corrected.json"
manifest_path.write_text(json.dumps(corrected_manifest, indent=2, allow_nan=False) + "\n")
report = {"corrected_manifest": str(manifest_path), "case": case,
          "archive_policy": "Original reference, manifest, original scores and all participant artifacts are preserved. This is a gold correction, not a new model attempt or a difficulty ratchet."}
(AUTHOR / "si_audit/correction.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
print(json.dumps(report, indent=2))
