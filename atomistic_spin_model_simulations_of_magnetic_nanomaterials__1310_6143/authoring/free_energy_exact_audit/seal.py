import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np

ROOT=Path(__file__).resolve().parent


def main():
    provenance=json.loads((ROOT/"provenance.json").read_text())
    for name,entry in provenance["source_files"].items():
        assert hashlib.sha256(Path(entry["original"]).read_bytes()).hexdigest()==entry["sha256"],name
        assert hashlib.sha256((ROOT/"source"/name).read_bytes()).hexdigest()==entry["sha256"],name
    assert hashlib.sha256((ROOT/"frozen_engine").read_bytes()).hexdigest()==provenance["binary_sha256"]
    status=json.loads((ROOT/"STATUS.json").read_text())
    oracle=json.loads((ROOT/"results/oracle.json").read_text())
    full=json.loads((ROOT/"results/full.json").read_text())
    durations=[]
    seeds=[]
    for path in (ROOT/"raw").glob("*.npz"):
        with np.load(path,allow_pickle=False) as data:
            durations.append(float(data["seconds"]))
            seeds.append(int(data["seed"]))
    assert len(seeds)==len(set(seeds)),"Reused random seeds"
    status.update(frozen_source_hashes_still_match=True,gates=full["gates"],raw_jobs=len(seeds),unique_seeds=len(set(seeds)),
                  maximum_native_job_seconds=max(durations),summed_native_job_seconds=sum(durations),
                  max_constraint_or_norm=full["max_constraint_or_norm"],
                  max_simpson_bias_over_sem=full["max_simpson_bias_over_sem"],
                  minimum_wrong_target_zmax=full["minimum_wrong_target_zmax"],
                  oracle_checks=oracle["checks"],
                  small_moment_probability_at_pi4={key:value["probability_moment_below_point2_at_pi4"]
                                                   for key,value in oracle["cases"].items()})
    (ROOT/"STATUS.json").write_text(json.dumps(status,indent=2)+"\n")
    hashes={}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name!="MANIFEST.json" and path.suffix!=".log" and "tmp" not in path.relative_to(ROOT).parts:
            hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest={"status":status["status"],"files_sha256":hashes,
              "write_scope":"authoring/free_energy_exact_audit only",
              "python":sys.version,"numpy":np.__version__,"machine":platform.machine(),
              "pilot_original_sources_rechecked":True,"notes":"Native timings are measured subprocess wall times under concurrent authoring load."}
    (ROOT/"MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(status),flush=True)


if __name__ == "__main__":
    main()
