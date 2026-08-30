import json
import os
from pathlib import Path
import re
import sys
import types


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
CHAMPION = CONCEPT / "champions" / "generation_2"


def load_champion(assets, output, iterations=250):
    sys.dont_write_bytecode = True
    assets = Path(os.environ.get("ASSETS", str(assets))).resolve()
    output = Path(output).resolve()
    config = json.loads((assets / "input" / "device.json").read_text())
    sys.path.insert(0, str(CHAMPION / "participant" / "workspace"))
    modules = []
    for name in ("optimize", "continuation", "discrete"):
        path = CHAMPION / "research" / (name + ".py")
        source = path.read_text()
        source = re.sub(r"\b64\b", "COUNT", source)
        source = re.sub(r"\b24\b", "BUDGET", source)
        source = source.replace(".375", "(BUDGET / COUNT)")
        if name == "optimize":
            source = re.sub(r"^ROOT = .*$", "ROOT = Path(" + repr(str(CHAMPION)) + ")", source, flags=re.M)
            source = source.replace("load_problem(ROOT / 'participant/input')", "load_problem(Path(" + repr(str(assets / "input")) + "))")
            source = re.sub(r"^OUT = .*$", "OUT = Path(" + repr(str(output)) + ")", source, flags=re.M)
        elif name == "continuation":
            source = source.replace("max_workers=BUDGET", "max_workers=24")
            source = source.replace("'maxiter':250", "'maxiter':STAGE_ITERATIONS")
        else:
            source = source.replace("6*delta", "self.config['pin_potential']*delta")
        module = types.ModuleType(name)
        module.__file__ = str(path)
        module.COUNT = len(config["candidates"])
        module.BUDGET = config["normal_site_count"]
        module.STAGE_ITERATIONS = iterations
        sys.modules[name] = module
        exec(compile(source, str(path), "exec"), module.__dict__)
        modules.append(module)
    return tuple(modules)
