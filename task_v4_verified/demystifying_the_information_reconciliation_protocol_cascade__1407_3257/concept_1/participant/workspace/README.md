# Public simulator workspace

The complete trusted-model source is `../cascade_sim.py`; scoring is
`../scoring.py`. `run.py` invokes that public scorer. All these task assets
are read-only. Write optimization scripts and artifacts in the writable
output directory provided by the runner, not here.

```sh
python3 workspace/run.py --policy /path/to/output/policy.json --split train --output /path/to/output/train_report.json
```
