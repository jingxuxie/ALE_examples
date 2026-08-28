import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
PAPER=ROOT.parents[1]
sys.path.insert(0,str(PAPER/"authoring"))
from isolated import run_submission


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("case")
    arguments=parser.parse_args()
    manifest=json.loads((ROOT/"manifest.json").read_text())
    entry=next(item for item in manifest if item["id"]==arguments.case)
    output=ROOT/"scouts"/entry["id"]/"output.json"
    metrics=run_submission(ROOT/"scout_submission",ROOT/entry["path"],output,
                           PAPER/"pilots/free_energy/participant",timeout=180,memory_gib=4)
    (output.parent/"execution.json").write_text(json.dumps(metrics,indent=2)+"\n")
    print(json.dumps({key:value for key,value in metrics.items() if key not in ["stdout","stderr"]}),flush=True)


if __name__ == "__main__":
    main()
