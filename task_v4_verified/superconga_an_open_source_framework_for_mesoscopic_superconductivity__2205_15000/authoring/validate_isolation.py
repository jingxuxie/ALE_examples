import json
import sys
from pathlib import Path

from sandbox import Sandbox

ROOT = Path(__file__).resolve().parents[1]


def main():
    concept = ROOT / "concept_2"
    denied = [concept / "evaluator" / "hidden" / "feasible_design" / "design.json",
              ROOT / "authoring" / "sources" / "paper.pdf", ROOT.parents[1] / "prompt_v6.txt"]
    if not all(path.exists() for path in denied):
        raise RuntimeError("negative-control files must actually exist on the host")
    script = "\n".join([
        "import json,os,socket,pathlib",
        "report={}",
        "report['participant_readable']=pathlib.Path('/participant/TASK.md').is_file()",
        "pathlib.Path('/output/probe').write_text('scratch')",
        "report['output_writable']=True",
        "report['private_reads']={}",
        "for name in " + repr([str(path) for path in denied]) + ":",
        "    try:",
        "        with open(name,'rb') as handle: handle.read(1)",
        "        report['private_reads'][name]='UNEXPECTED_ACCESS'",
        "    except OSError as error: report['private_reads'][name]=type(error).__name__",
        "try:",
        "    pathlib.Path('/participant/TASK.md').open('a').close()",
        "    report['participant_write']='UNEXPECTED_ACCESS'",
        "except OSError as error: report['participant_write']=type(error).__name__",
        "try:",
        "    pathlib.Path('/output/link').symlink_to(" + repr(str(denied[0])) + ")",
        "    pathlib.Path('/output/link').read_bytes()",
        "    report['symlink_escape']='UNEXPECTED_ACCESS'",
        "except OSError as error: report['symlink_escape']=type(error).__name__",
        "report['environment_keys']=sorted(os.environ)",
        "report['pid_namespace_processes']=[entry for entry in os.listdir('/proc') if entry.isdigit()]",
        "print(json.dumps(report))",
    ])
    with Sandbox(concept / "participant", concept / "participant" / "baseline", seconds=10) as isolated:
        run = isolated.run(["/usr/bin/python3", "-c", script])
    if run["returncode"] != 0:
        raise RuntimeError(run["stderr"])
    report = json.loads(run["stdout"])
    report["passed"] = bool(report["participant_readable"] and report["output_writable"]
                            and all(value != "UNEXPECTED_ACCESS" for value in report["private_reads"].values())
                            and report["participant_write"] != "UNEXPECTED_ACCESS"
                            and report["symlink_escape"] != "UNEXPECTED_ACCESS")
    (ROOT / "authoring" / "isolation_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise RuntimeError("isolation checks failed")


if __name__ == "__main__":
    main()
