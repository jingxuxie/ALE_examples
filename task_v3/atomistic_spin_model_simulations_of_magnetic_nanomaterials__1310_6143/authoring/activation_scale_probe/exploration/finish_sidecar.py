import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK = ROOT.parents[2]


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


profiles = {path.name: json.loads(path.read_text()) for path in sorted((ROOT / "structured_profiles").glob("*.json"))}
write(ROOT / "result.json", {"conclusion": "Eligible three-bottleneck scale prototype, but standard planar optimizations recover both N2048 cases cold in under20s. No intrinsic or persistent-hardness claim; ratchet decision belongs to main.", "native_interface": json.loads((ROOT / "interface/N2048/validation.json").read_text()), "profiles": profiles, "path_audits": [str(path.relative_to(ROOT)) for path in sorted((ROOT / "path_audits").glob("*.json"))], "provisional_scouting_manifest": "heldout/manifest.json"})
sources = [TASK / "pilots/activation/attempt/solve.py", ROOT.parent / "reference.py", TASK / "pilots/activation/private/build_references.py", TASK / "authoring/isolated.py"]
for name in ["libSpirit.so"]:
    sources.append(TASK / "authoring/spirit/core/python/spirit" / name)
for name in ["Method_GNEB.cpp", "Hamiltonian_Heisenberg.cpp", "HTST.cpp", "Sparse_HTST.cpp"]:
    sources.append(TASK / "authoring/spirit/core/src/engine" / name)
artifacts = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(ROOT.rglob("*")) if path.is_file() and path.name != "provenance.json"}
write(ROOT / "provenance.json", {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_revision": "e82250d3b14411c2c2fa292d143f13e3e111ad8c", "source_sha256": {str(path.relative_to(TASK)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}, "artifact_sha256": artifacts})
