import json

import numpy as np

import audit


def main():
    subsets = ((audit.SPINS + 1) / 2).astype(np.int8)
    independent = np.ones(65536, dtype=bool)
    adjacency = np.zeros((16, 16), dtype=np.int8)
    for first, second in audit.EDGES:
        adjacency[first, second] = 1
        adjacency[second, first] = 1
        independent &= ~((subsets[:, first] == 1) & (subsets[:, second] == 1))
    neighbor_counts = subsets @ adjacency
    necessary = np.all((neighbor_counts <= 2) | (subsets == 1), axis=1)
    dimensions = subsets.sum(axis=1)
    report = {"subsets_enumerated": 65536,
              "necessary_geometry_counts_by_free_dimension": {str(size): int(np.count_nonzero(independent & necessary & (dimensions == size))) for size in range(9)},
              "maximum_geometry_feasible_free_dimension": int(dimensions[independent & necessary].max()),
              "four_free_star_variance_lower_bound_at_floor_0.001_beta_1": 56 * 0.001 * 0.999,
              "scope": "necessary ground-cube geometry only; exact exhaustive subset check, not full Ising-class optimization"}
    assert report["maximum_geometry_feasible_free_dimension"] == 4
    audit.save("ground_cube_geometry.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
