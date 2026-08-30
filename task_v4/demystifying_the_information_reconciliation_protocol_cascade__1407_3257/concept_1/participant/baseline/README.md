# Runnable reference

`policy.json` is the 14-pass paper-inspired reference. The root-level copy
has the same contents. To emit a new copy into the runner's writable output
directory, run from the task root:

```sh
python3 baseline/run.py --output /path/to/output/policy.json
```

Do not overwrite these read-only baseline assets.
