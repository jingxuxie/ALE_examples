import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from case_factory import CHALLENGE_SEED, CONFIRMATION_SEED, SCREENING_SEED, split_cases
from physics import compile_case
from scoring import evaluate_controls, matrix_for, score_answer
from synthesis import synthesize, weak_controls


PRIVATE = Path(__file__).resolve().parent
PILOT = PRIVATE.parent


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(contents):
    return hashlib.sha256(contents.encode()).hexdigest()


def add_files(files):
    parts = ["*** Begin Patch"]
    for relative, contents in files.items():
        path = PILOT / relative
        if path.exists():
            raise RuntimeError("refusing to overwrite frozen artifact: " + str(path))
        parts.append("*** Add File: " + str(path))
        parts.extend("+" + line for line in contents.splitlines())
    parts.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(parts) + "\n", text=True, check=True, stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=7)
    arguments = parser.parse_args()
    if (PRIVATE / "manifest.json").exists():
        raise RuntimeError("already frozen; do not refreeze after participant runs")
    manifest = {"version": 1, "seeds": {"screening": SCREENING_SEED, "challenge": CHALLENGE_SEED,
                 "confirmation_reserved": CONFIRMATION_SEED}, "restarts": arguments.restarts,
                "splits": {}, "reference_method": "published-pattern initializers plus bounded discrete search",
                "baseline_method": "published short-period pattern; perfect privileged algebra"}
    report = {"splits": {}, "certificate_validation": "private/test_physics.py"}
    for split in ("screening", "challenge", "confirmation"):
        entries, scores = [], []
        for index, case in enumerate(split_cases(split)):
            started = time.monotonic()
            certificate = compile_case(case)
            matrix = matrix_for(case, certificate)
            weak = {"certificate": certificate, **weak_controls(case)}
            strong = {"certificate": certificate, **synthesize(case, matrix, 77119 + index, arguments.restarts)}
            anchors = {}
            raw = {}
            for name in ("analog", "digital"):
                weak_metrics = evaluate_controls(case, matrix, weak[name], name == "digital")
                strong_metrics = evaluate_controls(case, matrix, strong[name], name == "digital")
                if strong_metrics["quality"] <= weak_metrics["quality"] + 1e-7:
                    raise RuntimeError("constructive search did not improve weak anchor: " + case["id"] + " " + name)
                anchors[name] = {"weak": weak_metrics["quality"], "strong": strong_metrics["quality"]}
                raw[name] = {"weak": weak_metrics, "strong": strong_metrics}
            case_text = encoded(case) + "\n"
            payloads = {"strong": {"case_sha256": digest(encoded(case)), "answer": strong},
                        "weak": {"case_sha256": digest(encoded(case)), "answer": weak}}
            case_path = ("participant/input/screening/" if split == "screening" else "private/challenge_pool/" + split + "/") + case["id"] + ".json"
            reference_path = "private/reference/solutions/" + case["id"] + ".json"
            weak_path = "private/weak_reference/solutions/" + case["id"] + ".json"
            strong_text, weak_text = encoded(payloads["strong"]) + "\n", encoded(payloads["weak"]) + "\n"
            add_files({case_path: case_text, reference_path: strong_text, weak_path: weak_text})
            entries.append({"id": case["id"], "case_path": case_path, "case_file_sha256": digest(case_text),
                            "reference_path": reference_path, "reference_file_sha256": digest(strong_text),
                            "weak_path": weak_path, "weak_file_sha256": digest(weak_text), "anchors": anchors})
            strong_score = score_answer(case, certificate, strong, anchors)
            weak_score = score_answer(case, certificate, weak, anchors)
            if strong_score["score"] <= 0.9 or strong_score["algebra"] != 1:
                raise RuntimeError("reference validity failed")
            scores.append({"id": case["id"], "family": case["family"], "length": case["length"],
                           "reference": strong_score["score"], "weak": weak_score["score"],
                           "raw": raw, "seconds": time.monotonic() - started})
            print(case["id"], json.dumps(scores[-1]), flush=True)
        manifest["splits"][split] = entries
        report["splits"][split] = scores
    manifest["implementation_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                          for path in (PRIVATE / "physics.py", PRIVATE / "scoring.py", PRIVATE / "synthesis.py", PRIVATE / "case_factory.py")}
    add_files({"private/manifest.json": json.dumps(manifest, indent=2) + "\n",
               "private/reference/validation/precomputed.json": json.dumps(report, indent=2) + "\n"})


if __name__ == "__main__":
    main()
