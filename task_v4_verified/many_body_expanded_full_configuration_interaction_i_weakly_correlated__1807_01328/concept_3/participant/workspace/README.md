# Workspace entry point

The canonical workspace remains at `../input/workspace/`; files and datasets are not duplicated here. Read its `SCHEMA.md` and `MODEL.md`, use `data/` for the fixed datasets, and use `generator.py` for independent synthetic examples.

Treat participant assets as read-only. Write predictions, reports and other construction artifacts into your own writable output directory. The compatibility baseline entry point is `../baseline/run.py`; its README gives a command with explicit writable outputs.
