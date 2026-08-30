import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    attempts = []
    for metadata_path in ROOT.glob("concept_*/attempts/*.run.json"):
        record = json.loads(metadata_path.read_text())
        attempts.append((str(Path(record["output"]).resolve()), record["status"], metadata_path))
    live = []
    for process in Path("/proc").iterdir():
        if not process.name.isdecimal() or int(process.name) == os.getpid():
            continue
        try:
            command = (process / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            working = str((process / "cwd").resolve(strict=True))
            state = (process / "stat").read_text().rsplit(")", 1)[1].split()[0]
        except (OSError, ValueError):
            continue
        if state == "Z":
            continue
        for output, status, metadata in attempts:
            in_output = working == output or working.startswith(output + "/")
            mentioned_by_agent = False
            if output in command and not in_output:
                try:
                    entries = (process / "environ").read_bytes().split(b"\0")
                    prefix = ("CODEX_HOME=" + str(ROOT / "authoring/runtimes") + "/").encode()
                    mentioned_by_agent = any(entry.startswith(prefix) for entry in entries)
                except OSError:
                    pass
            if in_output or mentioned_by_agent:
                live.append(dict(pid=int(process.name), state=state, attempt=str(metadata.relative_to(ROOT)),
                                 recorded_status=status))
                break
    unexpected = [entry for entry in live if entry["recorded_status"] == "finished"]
    report = dict(passed=not unexpected and (not args.final or not live), final=args.final,
                  live_attempt_processes=live, unexpected_completed_attempt_processes=unexpected,
                  read_only_check=True, trusted_grading_processes_excluded=True)
    name = "final_process_audit.json" if args.final else "interim_process_audit.json"
    (ROOT / "authoring" / name).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
