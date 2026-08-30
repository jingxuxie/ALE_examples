import datetime
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def main():
    records = [json.loads(path.read_text()) for path in ROOT.glob("concept_*/attempts/v_*.metadata.json")]
    assert records and all("finished_utc" in record for record in records)
    removed = []
    for runtime in sorted((ROOT / "research").glob(".runtime-*")):
        assert runtime.is_dir() and not runtime.is_symlink()
        assert runtime.resolve().parent == (ROOT / "research").resolve()
        assert not (runtime / "auth.json").exists() and not (runtime / "auth.json").is_symlink()
        assert str(runtime) in {record["runtime"] for record in records}
        shutil.rmtree(runtime)
        removed.append(runtime.name)
    report = {"removed_finished_runtime_caches": removed,
              "kept_submissions_metadata_transcripts_scores": True,
              "global_codex_home_untouched": True,
              "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (ROOT / "research/runtime_cleanup.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
