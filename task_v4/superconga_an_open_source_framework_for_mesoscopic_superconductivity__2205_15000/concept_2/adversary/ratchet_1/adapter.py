import json
import os
from pathlib import Path
import re
import sys
import types


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]


def load_champion(assets, output):
    sys.dont_write_bytecode = True
    assets = Path(os.environ.get("ASSETS", str(assets))).resolve()
    output = Path(output).resolve()
    config = json.loads((assets / "input" / "device.json").read_text())
    sys.path.insert(0, str(CONCEPT / "participant" / "workspace"))
    modules = []
    for name in ("optimize", "continuation"):
        source_path = CONCEPT / "champions" / "generation_1" / (name + ".py")
        original = source_path.read_text()
        adapted = re.sub(r"\b64\b", "COUNT", original)
        adapted = re.sub(r"\b24\b", "BUDGET", adapted)
        adapted = adapted.replace("0.375", "(BUDGET / COUNT)")
        if name == "optimize":
            adapted = re.sub(r"^ASSETS = .*$", "ASSETS = Path(" + repr(str(assets)) + ")", adapted, flags=re.M)
            adapted = re.sub(r"^OUTPUT = .*$", "OUTPUT = Path(" + repr(str(output)) + ")", adapted, flags=re.M)
            adapted = adapted.replace("list(range(3))", "list(range(len(self.config['conditions'])))")
            adapted = adapted.replace("reshape(3, 8, 31)", "reshape(fit.target.shape)")
        module = types.ModuleType(name)
        module.__file__ = str(source_path)
        module.COUNT = len(config["candidates"])
        module.BUDGET = config["normal_site_count"]
        sys.modules[name] = module
        exec(compile(adapted, str(source_path), "exec"), module.__dict__)
        modules.append(module)
    return tuple(modules)


def adaptation_diff(assets, output):
    load_champion(assets, output)
    config = json.loads((Path(assets) / "input" / "device.json").read_text())
    return {
        "source": "champions/generation_1/{optimize.py,continuation.py}",
        "method": "in-memory source adaptation; originals never written",
        "substitutions": {
            "64": "COUNT = len(config['candidates'])",
            "24": "BUDGET = config['normal_site_count']",
            "0.375": "BUDGET / COUNT",
            "ASSETS": "explicit per-case assets path, overridable with ASSETS environment variable",
            "OUTPUT": "per-run ratchet_1 output path",
            "list(range(3))": "list(range(len(self.config['conditions'])))",
            "reshape(3, 8, 31)": "reshape(fit.target.shape), diagnostic only",
        },
        "unchanged": ["SpectralFit analytic resolvent Jacobian", "bounded scipy least_squares", "top-budget projection", "TransformedFit smoothing/cumulative/budget/binary penalties", "continuation stage schedules and tolerances"],
        "runner": "same functions and solver options; explicit deterministic starts, per-stage independent scoring and timing",
        "example_count": len(config["candidates"]),
    }
