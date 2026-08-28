import json
import pathlib

from engine import np, predict, simulate
from dense_cluster import embed, initial_indices, local_terms
from build import make_case, settings


def main():
    rows = []
    for spin, length, protection in [(0.5, 4, "full"), (1.0, 3, "linear")]:
        configuration = settings(length, spin, 4.0, protection, 113, True)
        parameters = [0.13, 0.08, -0.07]
        times = [0.0, 0.2, 0.5, 1.0]
        pairs = [[0, length - 1]]
        exact = simulate(configuration, parameters, times, pairs)
        approximate, meta = predict(configuration, parameters, times, pairs, step=0.00625, bond=64, cutoff=1e-14)
        errors = {name: float(np.max(abs(np.array(exact[name]) - approximate[name]))) for name in exact}
        sites, bonds, gauss, operators = local_terms(configuration, [0.0, 0.0, 0.0])
        local_dim = len(operators["identity"])
        hamiltonian = sum(embed(term, site, 1, length, local_dim) for site, term in sites.items())
        hamiltonian += sum(embed(term, left, 2, length, local_dim) for (left, right), term in bonds.items())
        commutators = []
        for site in range(length):
            constraint = embed(gauss[site], max(0, site - 1), 1 if site == 0 else 2, length, local_dim)
            commutators.append(float(np.linalg.norm(hamiltonian @ constraint - constraint @ hamiltonian)))
        rows.append({"spin": spin, "length": length, "protection": protection,
                     "max_errors_vs_exact": errors, "gauge_square_commutators": commutators,
                     "initial_max_violation": float(np.max(abs(np.array(exact["violation"])[0]))), "runtime": meta})
    output = pathlib.Path(__file__).with_name("small_system_validation.json")
    output.write_text(json.dumps(rows, indent=2))
    assert all(max(row["gauge_square_commutators"]) < 1e-10 for row in rows)
    assert all(max(row["max_errors_vs_exact"].values()) < 5e-5 for row in rows), rows
    print(json.dumps(rows), flush=True)


if __name__ == "__main__":
    main()
