import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
runner = ROOT.parents[1] / "run_allowlisted_codex.sh"
current = runner.read_text()
original = current.replace("# Commands launched by the child inherit a four-thread OpenMP/BLAS ceiling.\n", "")
original = original.replace(
    "# the narrower benchmark profile to this child process. OMP_THREAD_LIMIT is the\n"
    "# hard OpenMP ceiling; OMP_NUM_THREADS supplies the normal team-size default.\n"
    "# The other variables cap common numerical libraries that do not use OpenMP.\n",
    "# the narrower benchmark profile to this child process.\n")
variables = ["OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OMP_MAX_ACTIVE_LEVELS", "OMP_NESTED", "OMP_DYNAMIC",
             "OPENBLAS_NUM_THREADS", "GOTO_NUM_THREADS", "MKL_NUM_THREADS", "MKL_DYNAMIC", "BLIS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"]
original = "".join(line for line in original.splitlines(keepends=True)
                   if not any(line.startswith("  " + variable + "=") for variable in variables))
expected_original = "9625e083fce46db66609c63bca91b7177bd6165ac79e2efbfb02c8cc5aa43da3"
if hashlib.sha256(original.encode()).hexdigest() != expected_original:
    raise ValueError("runner changes exceed the reviewed numerical thread cap")
versions = {}
for text in [original, current]:
    digest = hashlib.sha256(text.encode()).hexdigest()
    path = ROOT / "authoring/runner_versions" / (digest + ".sh")
    if not path.exists():
        patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
        subprocess.run(["apply_patch", patch], check=True)
    versions[digest] = str(path.relative_to(ROOT))
report = {"passed": True, "original_sha256": expected_original,
          "updated_sha256": hashlib.sha256(current.encode()).hexdigest(),
          "versions": versions, "filesystem_allowlist_unchanged": True, "network_policy_unchanged": True,
          "change": "External shared-runner update adds four-thread numerical-library ceilings only. No runner edit was made by this session.",
          "applies_to": "concept_2 attempt v_3 used the updated runner; earlier scientific attempts used the original.",
          "evaluation": "Unchanged: one-core isolated executable evaluation; design evaluation executes no submitted code."}
(ROOT / "authoring/runner_version_audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
