import concurrent.futures
import json
from pathlib import Path

from generate import REFERENCE, ROOT, worker


def main():
    plan_path=REFERENCE/"refinement_plan.json"
    if plan_path.exists():
        plan=json.loads(plan_path.read_text())
    else:
        audit=json.loads((REFERENCE/"validation.json").read_text())
        plan={key:[item["angle"] for item in value["diagnostics"] if max(item["rhat"])>1.07]
              for key,value in audit["cases"].items()}
        plan={key:value for key,value in plan.items() if value}
        plan_path.write_text(json.dumps(plan,indent=2)+"\n")
        (REFERENCE/"validation_before_extension.json").write_text(json.dumps(audit,indent=2)+"\n")
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    cases={entry["id"]:json.loads((ROOT/entry["path"]).read_text())
           for entries in manifest.values() for entry in entries}
    jobs=[(cases[key],angle,chain,"extended",10000,30000)
          for key,angles in plan.items() for angle in angles for chain in range(4)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
        for token in executor.map(worker,jobs):
            print(token,flush=True)


if __name__ == "__main__":
    main()
