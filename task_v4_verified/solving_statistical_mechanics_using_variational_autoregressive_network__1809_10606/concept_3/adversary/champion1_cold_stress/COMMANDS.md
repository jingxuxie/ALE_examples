# Executed audit command

Working directory: this `champion1_cold_stress` directory. The command ran with `require_escalated`, because the host's bwrap sandbox hangs. No fresh agents were launched.

```bash
mkdir -p cache
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= TMPDIR="$PWD/cache" \
  taskset -c 380-383 python -u run48.py > audit.log 2>&1
```

`run48.py` writes the explicit query freeze before inference, freezes all predictions before opening private parameters, and saves exact labels and metrics. It refuses to overwrite an existing query freeze. Do not rerun in place or delete the freeze. Public-data fitted models and recovered science code are read-only inputs; private parameters are used only for exact evaluation after both freezes.

`commands.json` records the actual invocation, time, working directory, affinity and thread environment. `audit.log` records progress and complete metrics. `ARTIFACTS_FROZEN.json` hashes the completed numerical artifacts; this explanatory report and command document were added after scoring.
