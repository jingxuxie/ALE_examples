"""Recover transcript sources without reading secrets or writing outside this sidecar."""

import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


SIDE = Path(__file__).resolve().parent
CONCEPT = SIDE.parents[1]
TRANSCRIPT = CONCEPT / "attempts/v_1_run/transcript.log"
DESTINATION = SIDE / "recovered"
ALLOWED = {"infer.py", "fast_infer.py", "strip.cpp", "native.py", "posterior.py", "validate.py", "multistart.py"}


def main():
    if (SIDE / "SOURCE_PROVENANCE.json").exists():
        raise SystemExit("Sources already restored; refuse overwriting.")
    text = TRANSCRIPT.read_text()
    sources, provenance, commands = {}, {}, []
    pattern = re.compile(r"^(/bin/bash -\S+ .*?) in (/srv/[^\n]+)\n", re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(text):
        arguments = shlex.split(match.group(1))
        if len(arguments) != 3:
            raise ValueError("Unrecognized recorded shell quoting")
        command = arguments[2]
        line = text.count("\n", 0, match.start()) + 1
        commands.append({"transcript_line": line, "cwd": match.group(2), "command": command})
        for patch in re.finditer(r"^\*\*\* Begin Patch\n(.*?)^\*\*\* End Patch", command, re.MULTILINE | re.DOTALL):
            lines = patch.group(1).splitlines()
            index = 0
            while index < len(lines):
                if lines[index].startswith("*** Add File: "):
                    original = lines[index].split(": ", 1)[1]
                    name = Path(original).name
                    index += 1
                    content = []
                    while index < len(lines) and not lines[index].startswith("*** "):
                        if not lines[index].startswith("+"):
                            raise ValueError("Unexpected Add File patch line")
                        content.append(lines[index][1:])
                        index += 1
                    if name in ALLOWED:
                        if name in sources:
                            raise ValueError("Duplicate source addition")
                        sources[name] = "\n".join(content) + "\n"
                        provenance[name] = {"original_path": original, "exec_transcript_start_line": line,
                                            "recovery": "POSIX-decode recorded shell argument, then remove Add File patch prefixes"}
                else:
                    index += 1
    if set(sources) != ALLOWED:
        raise ValueError("Missing recorded Add File sources: " + repr(ALLOWED - set(sources)))
    lines = text.splitlines()
    summaries = []
    for index, line in enumerate(lines):
        if line.startswith("+++ b/") and line.endswith("/summarize.py") and index + 1 < len(lines):
            hunk = re.fullmatch(r"@@ -0,0 \+1,(\d+) @@", lines[index + 1])
            if hunk is None:
                continue
            count = int(hunk.group(1))
            body = lines[index + 2:index + 2 + count]
            if len(body) != count or not all(value.startswith("+") for value in body):
                continue
            source = "\n".join(value[1:] for value in body) + "\n"
            preceding = "\n".join(lines[max(0, index - 5):index])
            blob_match = re.search(r"index [0-9a-f]+\.\.([0-9a-f]{40})", preceding)
            if blob_match is None:
                continue
            encoded = source.encode()
            blob = hashlib.sha1(b"blob " + str(len(encoded)).encode() + b"\0" + encoded).hexdigest()
            if blob != blob_match.group(1):
                raise ValueError("Summarizer full-file diff does not match recorded Git blob")
            summaries.append((index + 1, source, blob))
    if not summaries:
        raise ValueError("No verifiable complete summarizer snapshot")
    summary_line, summary_source, blob = summaries[-1]
    sources["summarize.py"] = summary_source
    provenance["summarize.py"] = {"transcript_start_line": summary_line,
                                    "recovery": "Complete initial full-file diff, followed by the recorded successful Update File edit",
                                    "git_blob_sha1": blob, "verified_snapshots": len(summaries)}
    recorded_updates = []
    for execution in commands:
        command = execution["command"]
        if "*** Update File:" not in command or "/summarize.py\n" not in command:
            continue
        update = re.search(r"\*\*\* Update File: [^\n]+/summarize.py\n(.*?)\*\*\* End Patch", command, re.DOTALL)
        if update is None:
            continue
        old = [line[1:] for line in update.group(1).splitlines() if line.startswith("-")]
        new = [line[1:] for line in update.group(1).splitlines() if line.startswith("+")]
        if len(old) != 1 or len(new) != 1 or sources["summarize.py"].count(old[0]) != 1:
            raise ValueError("Unexpected summarizer update; manual provenance review required")
        sources["summarize.py"] = sources["summarize.py"].replace(old[0], new[0], 1)
        recorded_updates.append({"transcript_line": execution["transcript_line"], "old": old[0], "new": new[0]})
    if len(recorded_updates) != 1:
        raise ValueError("Expected the recorded summarizer thinning-removal update")
    provenance["summarize.py"]["recorded_updates"] = recorded_updates
    original_output = str(CONCEPT / "attempts/v_1")
    scientific_edits = []
    patch = ["*** Begin Patch"]
    for name, content in sources.items():
        relocated = content.replace(original_output, str(DESTINATION))
        if relocated != content:
            scientific_edits.append({"file": name, "old_output_root": original_output,
                                      "new_output_root": str(DESTINATION), "replacement_count": content.count(original_output)})
        provenance[name]["transcript_source_sha256"] = hashlib.sha256(content.encode()).hexdigest()
        provenance[name]["restored_source_sha256"] = hashlib.sha256(relocated.encode()).hexdigest()
        patch.append("*** Add File: " + str(DESTINATION / name))
        patch.extend("+" + line for line in relocated.splitlines())
    patch.append("*** End Patch")
    subprocess.run(["apply_patch", "\n".join(patch) + "\n"], check=True, cwd=SIDE)
    relevant = [command for command in commands if any(token in command["command"] for token in
                ("infer.py --maxiter", "posterior.py --prepare", "posterior.py --chain", "python summarize.py", "g++ -O3"))
                and "*** Add File:" not in command["command"]]
    record = {"transcript": str(TRANSCRIPT), "transcript_sha256": hashlib.sha256(text.encode()).hexdigest(),
              "sources": provenance, "path_only_relocations": scientific_edits,
              "science_changes": [], "recorded_commands": relevant,
              "cleanup_deletions_replayed": False,
              "summarizer_note": "Shell-created file recovered from complete final diff, including the recorded update removing prediction thinning."}
    (SIDE / "SOURCE_PROVENANCE.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"restored_sources": sorted(sources), "summarizer_blob": blob,
                      "path_only_relocations": scientific_edits, "recorded_commands": relevant}, indent=2))


if __name__ == "__main__":
    main()
