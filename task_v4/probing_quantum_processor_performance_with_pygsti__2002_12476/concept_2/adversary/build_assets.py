import hashlib
import json
import subprocess
from pathlib import Path

from prototype import circuits


ROOT = Path(__file__).resolve().parents[1]


def add_file(path, content):
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "\n".join("+" + line for line in content.splitlines()) + "\n*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    families = circuits()
    families = {"short": families["short"], **{"germ_" + key: families[key] for key in "I X Y XY XXY".split()},
                "guards": families["guards"]}
    content = json.dumps(families, indent=2) + "\n"
    for location in ["participant/input/calibration.json", "evaluator/hidden/calibration.json"]:
        add_file(ROOT / location, content)
    add_file(ROOT / "evaluator/hidden/specification.json", (ROOT / "participant/input/specification.json").read_text())
    manifest = {}
    for name in ["specification.json", "calibration.json"]:
        manifest[name] = hashlib.sha256((ROOT / "evaluator/hidden" / name).read_bytes()).hexdigest()
    add_file(ROOT / "evaluator/hidden/manifest.json", json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"family_sizes": {name: len(words) for name, words in families.items()},
                      "unique_circuits": len(set(sum(families.values(), []))),
                      "max_depth": max(map(len, sum(families.values(), []))), "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
