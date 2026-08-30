import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import aggregate, evaluate_device


def main():
    config = json.loads((ROOT / "participant/input/config.json").read_text())
    example = json.loads((ROOT / "participant/input/development.json").read_text())[0]
    case = {"id": "checker-selftest", "family": "public", "parameters": example["parameters"], "noise_seed": 81921}
    cases = {
        "public_truth_acceptance": "import json,sys\njson.loads(input())\nprint(json.dumps(" + repr({"type": "answer", "parameters": example["parameters"]}) + "),flush=True)\n",
        "nan_rejected": "import json\ninput()\nprint(json.dumps({'type':'answer','parameters':[float('nan')]*20}),flush=True)\n",
        "extra_query_rejected": "import json\nconfig=json.loads(input())['config']\nfor index in range(config['query_budget']+1):\n print(json.dumps({'type':'query','preparation':7,'time':0,'phases':[0]*6}),flush=True)\n input()\n",
        "private_files_inaccessible": "import json,os\ninput()\nassert not os.path.exists(" + repr(str(ROOT / "evaluator/hidden/devices.json")) + ")\nassert not os.path.exists('/task/../evaluator/hidden/devices.json')\nassert not os.path.exists('/home/xuandong/mnt/jingxu/ALE')\nassert os.path.exists('/task/input/config.json')\nprint(json.dumps(" + repr({"type": "answer", "parameters": example["parameters"]}) + "),flush=True)\n",
    }
    reports = {}
    for name, code in cases.items():
        with tempfile.TemporaryDirectory(prefix="xdiag-protocol-selftest-") as temporary:
            submission = Path(temporary)
            (submission / "solve.py").write_text(code)
            report = evaluate_device(submission, case, config)
            reports[name] = {key: value for key, value in report.items() if key not in ("transcript", "parameters")}
    assert reports["public_truth_acceptance"]["valid"]
    assert reports["public_truth_acceptance"]["normalized_rmse"] == 0
    assert not reports["nan_rejected"]["valid"]
    assert not reports["extra_query_rejected"]["valid"]
    assert reports["private_files_inaccessible"]["valid"]
    output = {"valid": True, "tests": reports, "note": "Truth is embedded only for a labeled public example to test acceptance. This is not a solver and demonstrates no hidden-device achievability."}
    (ROOT / "adversary/protocol_validation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"valid": True, "tests": list(reports)}, indent=2))


if __name__ == "__main__":
    main()
