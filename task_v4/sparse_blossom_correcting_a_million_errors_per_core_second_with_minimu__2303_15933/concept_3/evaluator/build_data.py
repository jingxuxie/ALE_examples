import hashlib
import json
from pathlib import Path
import secrets

from hidden.simulator import REGIMES, draw_rates, make_spec


ROOT = Path(__file__).resolve().parents[1]


def main():
    private_path = ROOT / "evaluator/hidden/episodes.json"
    if private_path.exists():
        raise RuntimeError("Refusing to regenerate frozen episodes")
    private = []
    training = []
    for regime in REGIMES:
        for index in range(4):
            spec = make_spec(regime, secrets.randbits(64))
            private.append({"id": "%s_%d" % (regime, index), "spec": spec,
                            "rates": draw_rates(spec, secrets.randbits(64)).tolist(),
                            "sample_seed": secrets.randbits(128)})
        for index in range(2):
            spec = make_spec(regime, 1200 + 100 * REGIMES.index(regime) + index)
            training.append({"id": "training_%s_%d" % (regime, index), "spec": spec,
                             "rates": draw_rates(spec, 2200 + 100 * REGIMES.index(regime) + index).tolist(),
                             "sample_seed": 3200 + 100 * REGIMES.index(regime) + index})
    private_path.write_text(json.dumps({"episodes": private}, indent=2) + "\n")
    (ROOT / "participant/input/training.json").write_text(json.dumps({"episodes": training}, indent=2) + "\n")
    (ROOT / "participant/input/targets.json").write_bytes((ROOT / "evaluator/hidden/targets.json").read_bytes())
    manifest = {"episodes_sha256": hashlib.sha256(private_path.read_bytes()).hexdigest(),
                "targets_sha256": hashlib.sha256((ROOT / "evaluator/hidden/targets.json").read_bytes()).hexdigest(),
                "private_episodes": len(private), "training_episodes": len(training)}
    (ROOT / "evaluator/hidden/freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
