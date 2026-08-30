import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "concept_2/evaluator"))
from design_common import load_case, read_design


def relation_map_exists(pairs):
    pivots = {}
    for source, target in pairs:
        while source:
            pivot = source.bit_length()
            if pivot not in pivots:
                pivots[pivot] = source, target
                break
            previous_source, previous_target = pivots[pivot]
            source ^= previous_source
            target ^= previous_target
        if not source and target:
            return False
    return True


def main():
    concept = ROOT / "concept_2"
    baseline = read_design(concept / "participant/baseline/design.json")
    alternate = read_design(concept / "attempts/v_2/design.json")
    checks = []
    for scale in [1, 2, 3]:
        case = load_case(concept / f"participant/input/scale_{scale}.json.gz")
        coordinates = {tuple(coordinate): index for index, coordinate in enumerate(case["data_coordinates"])}
        width = case["coordinate_period"][0]
        permutation = [coordinates[((width - horizontal) % width, vertical)]
                       for horizontal, vertical in case["data_coordinates"]]
        qubit_count = len(permutation)
        cells = case["slot_cells"]
        pattern_matches = all(baseline[cells[qubit]] == alternate[cells[permutation[qubit]]]
                              for qubit in range(qubit_count))
        pairs = [(case["columns"][phase * qubit_count + qubit][axis],
                  case["columns"][phase * qubit_count + permutation[qubit]][axis])
                 for phase in range(case["noisy_subrounds"])
                 for qubit in range(qubit_count) for axis in range(3)]
        joint = relation_map_exists(pairs) and relation_map_exists([(target, source) for source, target in pairs])
        syndrome_pairs = [(source >> 4, target >> 4) for source, target in pairs]
        syndrome = relation_map_exists(syndrome_pairs) and relation_map_exists(
            [(target, source) for source, target in syndrome_pairs])
        assert pattern_matches and joint and syndrome
        checks.append({"scale": scale, "columns_checked": len(pairs), "pattern_matches": pattern_matches,
                       "joint_relations_preserved_both_directions": joint,
                       "syndrome_relations_preserved_both_directions": syndrome})
    result = {"passed": True, "checks": checks,
              "conclusion": "The first dense fresh submission and the supplied champion have equal population correctability under IID flagged supports. The reflected column permutation preserves all joint and syndrome linear dependencies, so both ranks, and therefore their difference, agree on every corresponding support. A finite hidden-sample score difference is not a genuine population improvement."}
    (concept / "adversary/reflection_equivalence.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
