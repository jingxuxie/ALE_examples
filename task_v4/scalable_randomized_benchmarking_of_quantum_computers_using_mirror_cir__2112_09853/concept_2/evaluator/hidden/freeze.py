import hashlib
import json
from pathlib import Path
import secrets
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True
from model import Episode, FAMILIES, SHAPES


def freeze():
    hidden = Path(__file__).resolve().parent
    root = hidden.parents[1]
    if (hidden / "benchmark.json").exists() or (hidden / "manifest.json").exists():
        raise RuntimeError("benchmark_already_frozen")
    cases = []
    for family in FAMILIES:
        for shape in SHAPES:
            seed = secrets.token_hex(16)
            episode = Episode(int(seed, 16), family, shape)
            target_bytes = json.dumps(episode.targets, separators=(",", ":")).encode()
            parameter_bytes = json.dumps({"idle": episode.idle, "base": episode.base.tolist(),
                                         "cross": episode.crosstalk.tolist(),
                                         "spam_intercept": episode.spam_intercept,
                                         "spam_edges": episode.spam_edges.tolist(),
                                         "spam_density": episode.spam_density,
                                         "drift": [episode.drift_amplitude, episode.drift_frequency,
                                                   episode.drift_phase, episode.drift_slope]},
                                        sort_keys=True, separators=(",", ":")).encode()
            cases.append({"id": family + "_" + "x".join(map(str, shape)),
                          "family": family, "shape": list(shape), "seed_hex": seed,
                          "targets_sha256": hashlib.sha256(target_bytes).hexdigest(),
                          "parameters_sha256": hashlib.sha256(parameter_bytes).hexdigest()})
    target = json.loads((root / "participant/input/limits.json").read_text())
    benchmark = {"benchmark_id": "mrb-active-v3", "generation": 3, "frozen_utc": datetime.now(timezone.utc).isoformat(),
                 "seed_source": "independent secrets.token_hex(16); disjoint from public small-integer development seeds",
                 "fixed_before_fresh_attempts": True, "target": target, "episodes": cases}
    (hidden / "benchmark.json").write_text(json.dumps(benchmark, indent=2) + "\n")
    trusted = [root / "evaluator/evaluate.py", hidden / "model.py", hidden / "transport.py",
               hidden / "selfcheck.py", hidden / "freeze.py", hidden / "benchmark.json",
               root / "participant/input/limits.json", root / "participant/workspace/MODEL.md",
               root / "participant/workspace/API.md", root / "participant/TASK.md",
               root / "participant/workspace/model.py", root / "participant/workspace/transport.py",
               root / "participant/workspace/develop.py", root / "participant/baseline/policy.py"]
    manifest = {"frozen_utc": benchmark["frozen_utc"], "files": {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in trusted}}
    (hidden / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"frozen": True, "episodes": len(cases),
                      "manifest_sha256": hashlib.sha256((hidden / "manifest.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    freeze()
