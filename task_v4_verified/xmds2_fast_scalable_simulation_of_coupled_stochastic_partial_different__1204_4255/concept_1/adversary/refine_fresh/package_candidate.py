import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
from measure import HERE, ROOT


def main():
    selection = json.loads((HERE / "portfolio_selection.json").read_text())
    candidate = HERE / "candidate"
    configs = []
    for spec in selection["configs"]:
        version = spec["version"]
        source_name = "engine.cpp" if version.startswith("v1") else "planner.cpp"
        binary_name = "planner_" + version
        shutil.copy2(HERE / "sources" / version / "planner", candidate / binary_name)
        shutil.copy2(HERE / "sources" / version / source_name, candidate / (binary_name + ".cpp"))
        configs.append({"binary": binary_name, "protocol": "v1" if version.startswith("v1") else "v2", "env": spec.get("env", {})})
    shutil.copy2(ROOT / "participant" / "baseline" / "solve.py", candidate / "baseline.py")
    (candidate / "config.json").write_text(json.dumps(configs, indent=2) + "\n")
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in candidate.iterdir() if path.is_file()}
    (HERE / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"candidate": str(candidate), "configs": configs, "files": sorted(manifest)}, indent=2))


if __name__ == "__main__":
    main()
