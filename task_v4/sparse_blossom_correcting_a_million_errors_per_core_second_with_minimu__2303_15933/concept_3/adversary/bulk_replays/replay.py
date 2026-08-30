import sys

sys.dont_write_bytecode = True

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil


SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import aggregate, run_episode


def check_unchanged():
    manifest = json.loads((SIDE / "manifest.json").read_text())
    expected = manifest["frozen_files"]
    actual = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for folder in ("participant", "evaluator") for path in (ROOT / folder).rglob("*") if path.is_file()}
    assert actual == expected
    assert hashlib.sha256((ROOT / "attempts/v_1_result.json").read_bytes()).hexdigest() == manifest["official_result_sha256"]
    for policy in ("candidate", "reference"):
        assert hashlib.sha256((ROOT / manifest[policy + "_source"]).read_bytes()).hexdigest() == manifest[policy + "_sha256"]
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tape", choices=("tape_1", "tape_2", "tape_3", "official_reproduction"), required=True)
    parser.add_argument("--episodes", nargs="+")
    parser.add_argument("--trace-candidate", action="store_true")
    arguments = parser.parse_args()
    manifest = check_unchanged()
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    if arguments.episodes:
        episodes = [episode for episode in episodes if episode["id"] in arguments.episodes]
    label = arguments.tape + ("_trace" if arguments.trace_candidate else "")
    reports = {"candidate": [], "reference": []}
    policies = ("candidate",) if arguments.trace_candidate else ("candidate", "reference")
    for original in episodes:
        for policy in policies:
            episode = copy.deepcopy(original)
            if arguments.tape != "official_reproduction":
                episode["sample_seed"] = manifest["tapes_declared_before_replay"][arguments.tape][episode["id"]]
            workspace = SIDE / "workspaces" / label / policy / episode["id"] / "submission"
            workspace.mkdir(parents=True, exist_ok=False)
            source = ROOT / manifest[policy + "_source"]
            shutil.copyfile(source, workspace / "solution.py")
            assert hashlib.sha256((workspace / "solution.py").read_bytes()).hexdigest() == manifest[policy + "_sha256"]
            command = ["/usr/bin/python3", "/submission/solution.py"]
            if policy == "reference":
                command += ["--policy", "robust"]
            if arguments.trace_candidate:
                shutil.copyfile(SIDE / "trace_wrapper.py", workspace / "trace_wrapper.py")
                command = ["/usr/bin/python3", "/submission/trace_wrapper.py"]
            transcript = SIDE / "transcripts" / label / policy / (episode["id"] + ".json")
            transcript.parent.mkdir(parents=True, exist_ok=True)
            result = run_episode(episode, workspace, command, transcript)
            result["source_copy_sha256"] = hashlib.sha256((workspace / "solution.py").read_bytes()).hexdigest()
            result["source_unchanged"] = result["source_copy_sha256"] == manifest[policy + "_sha256"]
            reports[policy].append(result)
            print(json.dumps({"tape": label, "policy": policy, **result}), flush=True)
            output = {"supplementary_only": True, "replaces_official_score": False,
                      "tape": label, "instrumented": arguments.trace_candidate,
                      "policies": {name: aggregate(rows) for name, rows in reports.items() if rows}}
            (SIDE / (label + "_report.json")).write_text(json.dumps(output, indent=2) + "\n")
    check_unchanged()


if __name__ == "__main__":
    main()
