import functools
import itertools
import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh


@functools.lru_cache(maxsize=2)
def sector(length=12):
    states = np.array(sorted(sum(1 << site for site in occupied)
                             for occupied in itertools.combinations(range(length), length // 2)), dtype=np.int64)
    spins = ((states[:, None] >> np.arange(length)) & 1).astype(float) - 0.5
    lookup = {int(state): index for index, state in enumerate(states)}
    exchange = np.diag(np.sum(spins * np.roll(spins, -1, axis=1), axis=1))
    for column, state in enumerate(states):
        for site in range(length):
            neighbour = (site + 1) % length
            if ((state >> site) & 1) != ((state >> neighbour) & 1):
                row = lookup[int(state ^ (1 << site) ^ (1 << neighbour))]
                exchange[row, column] += 0.5
    return states, spins, exchange


def hamiltonian(fields):
    fields = np.asarray(fields, dtype=float)
    if fields.shape != (12,) or not np.isfinite(fields).all():
        raise ValueError("fields must be twelve finite real numbers")
    states, spins, exchange = sector(len(fields))
    matrix = exchange.copy(order="F")
    matrix.flat[::len(states) + 1] += spins @ fields
    return matrix


def spectrum(fields, driver="evr"):
    return eigh(hamiltonian(fields), eigvals_only=True, driver=driver,
                overwrite_a=True, check_finite=False)


def ratios(energies):
    energies = np.asarray(energies, dtype=float)
    gaps = np.diff(energies)
    if len(gaps) < 2 or not np.isfinite(gaps).all() or np.any(gaps <= 1e-10):
        raise ValueError("insufficient or numerically degenerate spectrum")
    return np.minimum(gaps[:-1], gaps[1:]) / np.maximum(gaps[:-1], gaps[1:])


def symmetry_distance(fields):
    fields = np.asarray(fields, dtype=float)
    distances = []
    for reflected in (False, True):
        source = fields[::-1] if reflected else fields
        for shift in range(len(fields)):
            for sign in (-1, 1):
                if not reflected and shift == 0 and sign == 1:
                    continue
                distances.append(float(np.sqrt(np.mean((fields - sign * np.roll(source, shift)) ** 2))))
    return min(distances)


def validate_fields(fields, derived=False):
    fields = np.asarray(fields, dtype=float)
    if fields.shape != (12,) or not np.isfinite(fields).all():
        raise ValueError("fields must be twelve finite real numbers")
    if abs(float(np.mean(fields))) > 1e-9:
        raise ValueError("fields must have zero mean within 1e-9")
    bound = 8.5 if derived else 8.0
    minimum_rms = 0.55 if derived else 0.65
    minimum_distance = 0.05 if derived else 0.12
    minimum_separation = 1e-7 if derived else 0.001
    if float(np.max(np.abs(fields))) > bound:
        raise ValueError(f"absolute field exceeds {bound}")
    if float(np.sqrt(np.mean(fields ** 2))) < minimum_rms:
        raise ValueError(f"field rms is below {minimum_rms}")
    if float(np.min(np.diff(np.sort(fields)))) < minimum_separation:
        raise ValueError(f"field pair separation is below {minimum_separation}")
    distance = symmetry_distance(fields)
    if distance < minimum_distance:
        raise ValueError(f"signed dihedral symmetry distance is below {minimum_distance}")
    return {"maximum_absolute_field": float(np.max(np.abs(fields))),
            "rms_field": float(np.sqrt(np.mean(fields ** 2))),
            "pair_separation": float(np.min(np.diff(np.sort(fields)))),
            "symmetry_distance": distance}


def validate_witness(witness):
    if not isinstance(witness, dict) or set(witness) != {"schema_version", "fields", "orientation"}:
        raise ValueError("exactly schema_version, fields, orientation are required")
    if type(witness["schema_version"]) is not int or witness["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    if type(witness["orientation"]) is not int or witness["orientation"] not in (-1, 1):
        raise ValueError("orientation must be integer -1 or +1")
    fields = witness["fields"]
    if not isinstance(fields, list) or len(fields) != 12:
        raise ValueError("fields must be a JSON list of length twelve")
    if any(type(value) not in (int, float) for value in fields):
        raise ValueError("field entries must be numbers, not booleans or strings")
    return validate_fields(fields)


def proxy_statistics(energies):
    energies = np.asarray(energies, dtype=float)
    if energies.shape != (924,) or not np.isfinite(energies).all():
        raise ValueError("expected the full 924-level spectrum")
    ratios(energies)
    rank_r = float(np.mean(ratios(energies[308:616])))
    bandwidth = float(energies[-1] - energies[0])
    windows = []
    for target in (0.49, 0.50, 0.51):
        target_energy = energies[0] + target * bandwidth
        center = int(np.argmin(np.abs(energies - target_energy)))
        start = max(0, min(796, center - 64))
        windows.append({"target_density": target, "nearest_rank": center,
                        "start": start, "stop": start + 128, "ratio_count": 126,
                        "r": float(np.mean(ratios(energies[start:start + 128])))})
    proxy_r = float(np.mean([window["r"] for window in windows]))
    return {"rank_r": rank_r, "proxy_r": proxy_r, "difference": proxy_r - rank_r,
            "rank_ratio_count": 306, "windows": windows,
            "minimum_gap": float(np.min(np.diff(energies))),
            "bandwidth": bandwidth}


def family_fields(fields, protocol):
    fields = np.asarray(fields, dtype=float)
    for family in protocol["families"]:
        for member, offset in enumerate(family["offsets"]):
            yield family["name"], member, family["scale"] * fields + np.asarray(offset)


def assess(witness, protocol, driver="evr", counter=None):
    constraints = validate_witness(witness)
    fields = np.asarray(witness["fields"], dtype=float)
    orientation = witness["orientation"]
    profiles = [(family, member, perturbed, validate_fields(perturbed, derived=True))
                for family, member, perturbed in family_fields(fields, protocol)]
    def measure(profile):
        if counter is not None:
            counter["diagonalizations"] += 1
        return proxy_statistics(spectrum(profile, driver=driver))
    base = measure(fields)
    base["signed_difference"] = orientation * base["difference"]
    rows = []
    for family, member, perturbed, member_constraints in profiles:
        result = measure(perturbed)
        rows.append({"family": family, "member": member, **result,
                     "signed_difference": orientation * result["difference"],
                     "constraints": member_constraints})
    targets = protocol["targets"]
    summaries = []
    for family in protocol["families"]:
        members = [row for row in rows if row["family"] == family["name"]]
        differences = [row["signed_difference"] for row in members]
        summaries.append({"family": family["name"], "members": len(members),
                          "mean": float(np.mean(differences)), "minimum": min(differences),
                          "above_member_floor": sum(value >= targets["member_floor"] for value in differences)})
    core = float(np.mean([family["mean"] for family in summaries]))
    worst = min(summaries, key=lambda family: family["mean"])
    checks = {"core": core >= targets["core"],
              "worst_family": worst["mean"] >= targets["worst_family"],
              "base": base["signed_difference"] >= targets["base"],
              "member_coverage": all(family["above_member_floor"] >= targets["members_required"] for family in summaries)}
    return {"valid": True, "pass": all(checks.values()), "core": core,
            "worst_family": worst["mean"], "worst_family_name": worst["family"],
            "reason": "counterexample_verified" if all(checks.values()) else "below_target:" + ",".join(name for name, passed in checks.items() if not passed),
            "checks": checks, "base": base, "families": summaries, "members": rows,
            "constraints": constraints, "targets": targets, "diagonalizations": len(rows) + 1}
