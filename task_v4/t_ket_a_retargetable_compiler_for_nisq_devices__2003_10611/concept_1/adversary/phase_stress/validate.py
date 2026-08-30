import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
import generate


def main():
    root = Path(__file__).resolve().parent
    records = list(json.loads((root / "certificates.json").read_text()).values())
    rows = generate.validate_records(records)
    manifest = json.loads((root / "manifest.json").read_text())
    assert len(rows) == manifest["case_count"]
    cases = json.loads((root / "cases.json").read_text())
    assert {case["id"]: case for case in cases} == {record["case"]["id"]: record["case"] for record in records}
    for record in records:
        assert manifest["baseline"][record["case"]["id"]] == record["design"]["baseline"]
    for filename, expected in manifest["source_sha256"].items():
        assert generate.digest(Path(filename)) == expected
    freeze = json.loads((root / "freeze.json").read_text())
    for filename, expected in freeze["sha256"].items():
        assert generate.digest(root / filename) == expected
    print(json.dumps({"valid": True, "exact_certificates_checked": len(rows),
                      "complete": manifest["complete"], "frozen_hashes_verified": True,
                      "minimum_certificate_improvement": min(row["improvement"] for row in rows)}, indent=2))


if __name__ == "__main__":
    main()
