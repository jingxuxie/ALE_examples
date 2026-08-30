import json
from pathlib import Path

from generate import make_case


def main():
    directory = Path(__file__).resolve().parent / "broad_search"
    directory.mkdir(exist_ok=True)
    families = ["bond_charge", "overlapping_clusters", "multiscale"]
    cases, records = [], []
    for index in range(90):
        dimension = [10, 12, 14, 16, 18, 20][(index // 3) % 6]
        family = families[index % 3]
        case, _, record = make_case(803921 + index * 1009, family, dimension, dimension - 2, f"search_{index:03d}")
        cases.append(case)
        record["dimension"] = dimension
        records.append(record)
    (directory / "cases.json").write_text(json.dumps({"cases": cases, "seconds_per_case": 12}, allow_nan=False))
    (directory / "generation.json").write_text(json.dumps({"count": len(cases), "dimensions": [10, 12, 14, 16, 18, 20], "families": families, "records": records, "purpose": "Private broad comparison against future champions; outside-range cases may only enter a new explicitly disclosed task generation."}, indent=2))
    print(f"Prepared {len(cases)} private cases")


if __name__ == "__main__":
    main()
