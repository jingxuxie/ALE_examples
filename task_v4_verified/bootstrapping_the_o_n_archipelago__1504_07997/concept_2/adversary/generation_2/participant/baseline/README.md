# Standalone baseline

```
python baseline/solve.py input/instances.json output/answer.json
```

The positional arguments are the input JSON file and output JSON file. Optional
`--seconds-per-case` defaults to 300. The output parent must be writable; input,
participant and baseline directories may be read-only. Temporary state lives
beneath the output parent and is removed after each case. Diagnostics go to
stderr; the output file is updated after each completed case.

All supplied Python modules are required beside `solve.py`. No stored answers or
old input paths are included. Use the public checker to assess resulting data.
