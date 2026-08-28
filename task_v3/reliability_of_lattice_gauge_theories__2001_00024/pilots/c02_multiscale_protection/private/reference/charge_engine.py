import logging
import math
import time

from engine import np
from dense_cluster import initial_indices, local_terms
from tenpy.algorithms.tebd import TEBDEngine
from tenpy.linalg import np_conserved as npc
from tenpy.models.lattice import IrregularLattice, Lattice
from tenpy.models.model import NearestNeighborModel
from tenpy.networks.mps import MPS
from tenpy.networks.site import Site

logging.getLogger("tenpy").setLevel(logging.ERROR)


def predict(settings, parameters, times, pairs, step=0.0125, bond=128, cutoff=1e-13):
    start = time.monotonic()
    onsite, bonds, gauss, operators = local_terms(settings, parameters)
    length = settings["length"]
    dimension = len(operators["identity"])
    link_dimension = dimension // 2
    number = operators["number"]
    flux = operators["flux"]
    identity = operators["identity"]
    charge_info = npc.ChargeInfo([1], ["staggered_matter_number"])
    sites = []
    for site in range(length):
        charges = np.repeat([0, (-1) ** site], link_dimension)[:, None]
        leg = npc.LegCharge.from_qflat(charge_info, charges)
        sites.append(Site(leg, state_labels=[str(index) for index in range(dimension)], sort_charge=False,
                          number=number, flux=flux, flux_sq=flux @ flux,
                          flux_number=flux + number, flux_number_sq=(flux + number) @ (flux + number),
                          gauss0_sq=gauss[0]))
    cells = (length + 1) // 2
    lattice = Lattice([cells], sites[:2], bc="open", bc_MPS="finite",
                      basis=np.array([[2.0]]), positions=np.array([[0.0], [1.0]]))
    if length % 2:
        lattice = IrregularLattice(lattice, remove=[[cells - 1, 1]])
    bond_operators = [None]
    charge_residual = 0.0
    for left in range(length - 1):
        right = left + 1
        left_weight = 1.0 if left == 0 else 0.5
        right_weight = 1.0 if right == length - 1 else 0.5
        matrix = bonds[left, right] + left_weight * np.kron(onsite[left], identity)
        matrix += right_weight * np.kron(identity, onsite[right])
        charge = (-1) ** left * np.kron(number, identity) + (-1) ** right * np.kron(identity, number)
        charge_residual = max(charge_residual, float(np.linalg.norm(matrix @ charge - charge @ matrix)))
        legs = [sites[left].leg, sites[right].leg, sites[left].leg.conj(), sites[right].leg.conj()]
        bond_operators.append(npc.Array.from_ndarray(matrix.reshape([dimension] * 4), legs,
                                                     labels=["p0", "p1", "p0*", "p1*"], qtotal=[0]))
    model = NearestNeighborModel(lattice, bond_operators)
    state = MPS.from_product_state(sites, initial_indices(settings), bc="finite", dtype=complex,
                                   permute=False, unit_cell_width=cells)
    evolution = TEBDEngine(state, model, {"order": 4,
                            "trunc_params": {"chi_max": bond, "svd_min": 1e-13, "trunc_cut": math.sqrt(cutoff)}})
    output = {"parameters": list(parameters), "density": [], "violation": [], "correlation": []}
    previous_time = 0.0
    largest_bond = 1
    for current_time in times:
        duration = float(current_time) - previous_time
        if duration > 1e-14:
            steps = max(1, int(math.ceil(duration / step - 1e-9)))
            evolution.run_evolution(steps, duration / steps)
        density = np.real(state.expectation_value("number"))
        flux_square = np.real(state.expectation_value("flux_sq"))
        right_square = np.real(state.expectation_value("flux_number_sq"))
        violation = [float(np.real(state.expectation_value("gauss0_sq", sites=[0])[0]))]
        for site in range(1, length):
            cross = state.expectation_value_term([("flux", site - 1), ("flux_number", site)])
            violation.append(float(flux_square[site - 1] + right_square[site] + 2 * np.real(cross)))
        correlations = []
        for left, right in pairs:
            joint = state.expectation_value_term([("number", left), ("number", right)])
            correlations.append(float(np.real(joint) - density[left] * density[right]))
        output["density"].append(density.tolist())
        output["violation"].append(violation)
        output["correlation"].append(correlations)
        largest_bond = max(largest_bond, max(state.chi))
        previous_time = float(current_time)
    metadata = {"engine": "physics-tenpy-1.1.0", "seconds": time.monotonic() - start,
                "step": step, "bond_limit": bond, "cutoff": cutoff, "order": 4,
                "max_bond": largest_bond, "discarded_weight_sum": float(evolution.trunc_err.eps),
                "conserved_charge_commutator": charge_residual,
                "final_total_charge": state.get_total_charge(only_physical_legs=True).tolist()}
    return output, metadata
