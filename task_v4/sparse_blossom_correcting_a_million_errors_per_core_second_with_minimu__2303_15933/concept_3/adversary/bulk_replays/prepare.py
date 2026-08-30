import hashlib
import json
from pathlib import Path
import secrets
import shutil


SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = SIDE / "manifest.json"
    if path.exists():
        raise RuntimeError("Replay tapes already declared; refusing regeneration")
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    candidate = ROOT / "attempts/v_1_frozen_submission/solution.py"
    reference = ROOT / "adversary/portfolio/reference/solution.py"
    official = ROOT / "attempts/v_1_result.json"
    audit = json.loads((ROOT / "attempts/v_1_evaluation_audit.json").read_text())
    assert digest(candidate) == audit["frozen_submission_sha256"]["solution.py"]
    seeds = {"tape_%d" % tape: {episode["id"]: secrets.randbits(128) for episode in episodes} for tape in range(1, 4)}
    values = [seed for tape in seeds.values() for seed in tape.values()]
    assert len(set(values)) == 36 and not set(values).intersection(episode["sample_seed"] for episode in episodes)
    frozen = {str(source.relative_to(ROOT)): digest(source) for directory in ("participant", "evaluator")
              for source in (ROOT / directory).rglob("*") if source.is_file()}
    manifest = {"purpose": "supplementary noise sensitivity only; never replaces official score",
                "tapes_declared_before_replay": seeds,
                "paired_seed_note": "Each policy gets the same seed label within a tape/episode. Adaptive actions and query grouping differ, so observations are not identical or shotwise coupled.",
                "candidate_source": str(candidate.relative_to(ROOT)), "candidate_sha256": digest(candidate),
                "reference_source": str(reference.relative_to(ROOT)), "reference_sha256": digest(reference),
                "official_result_sha256": digest(official), "frozen_files": frozen,
                "targets_changed": False, "parameters_changed": False, "fresh_feedback": False}
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copyfile(ROOT / "participant/input/model.py", SIDE / "trusted_model.py")


if __name__ == "__main__":
    main()
