import numpy as np


def assemble(model):
    sites = model["sites"]
    basis = np.array([bits for bits in range(2 ** sites) if bin(bits).count("1") == model["up_spins"]])
    identity = np.eye(2, dtype=complex)
    spin_x = np.array([[0, 0.5], [0.5, 0]], dtype=complex)
    spin_y = np.array([[0, 0.5j], [-0.5j, 0]], dtype=complex)
    spin_z = np.diag([-0.5, 0.5]).astype(complex)

    def product(operators):
        result = np.ones((1, 1), dtype=complex)
        for site in reversed(range(sites)):
            result = np.kron(result, operators.get(site, identity))
        return result[np.ix_(basis, basis)]

    fields = np.array([product({site: spin_z}) for site in range(sites)])
    nearest_xy, nearest_zz, next_xy, next_zz, currents = [], [], [], [], []
    for site in range(sites):
        neighbor = (site + 1) % sites
        next_neighbor = (site + 2) % sites
        nearest_xy.append(product({site: spin_x, neighbor: spin_x}) + product({site: spin_y, neighbor: spin_y}))
        nearest_zz.append(product({site: spin_z, neighbor: spin_z}))
        next_xy.append(product({site: spin_x, next_neighbor: spin_x}) + product({site: spin_y, next_neighbor: spin_y}))
        next_zz.append(product({site: spin_z, next_neighbor: spin_z}))
        currents.append(product({site: spin_x, neighbor: spin_y}) - product({site: spin_y, neighbor: spin_x}))
    nearest_xy, nearest_zz = np.array(nearest_xy), np.array(nearest_zz)
    next_xy, next_zz, currents = np.array(next_xy), np.array(next_zz), np.array(currents)
    drifts = []
    for calibration in model["calibrations"]:
        drift = model["nearest_exchange"] * np.sum(nearest_xy + (model["nearest_anisotropy"] + calibration["anisotropy_shift"]) * nearest_zz, axis=0)
        drift += model["next_exchange"] * (1 + calibration["next_exchange_fraction"]) * np.sum(next_xy + model["next_anisotropy"] * next_zz, axis=0)
        field = np.array(model["static_field"]) + calibration["field_offset"] * np.array(model["field_error_profile"])
        drift += np.einsum("s,sij->ij", field, fields)
        drifts.append(drift)
    controls = np.array([
        np.einsum("s,sij->ij", model["staggered_profile"], fields),
        np.einsum("s,sij->ij", model["bond_profile"], nearest_xy + model["bond_control_anisotropy"] * nearest_zz),
        np.einsum("s,sij->ij", model["current_profile"], currents),
    ])
    initial = np.zeros((len(basis), len(model["initial_bitstrings"])), dtype=complex)
    for column, bits in enumerate(model["initial_bitstrings"]):
        initial[np.flatnonzero(basis == bits)[0], column] = 1
    return basis, np.array(drifts), controls, initial
