"""Analytical, high-precision, invariance, and executable-interface tests."""

import copy
from decimal import Decimal, localcontext
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from solve import FIELD_FACTOR, GYROMAGNETIC_RATIO, reduce_channels, solve


ROOT = Path(__file__).resolve().parent


def material(sublattice=0, rho=2.0, spin_rho=4.0, moment=2.0,
             alpha=0.1, eta=0.6, beta=0.2):
    return dict(sublattice=sublattice, rho_ohm_m=rho, rho_spin_ohm_m=spin_rho,
                moment_muB=moment, alpha=alpha, eta=eta, beta=beta)


def atom(cell, material_id, spin):
    return dict(cell=cell, material=material_id, spin=list(spin))


def make_case(stacks, materials, atoms, voltage=6.0, direction=1):
    return dict(version=1, case_id="synthetic", stacks=stacks, materials=materials,
                atoms=atoms, voltage_V=voltage, direction=direction,
                cell_length_m=1.0, cell_area_m2=1.0,
                num_sublattices=max(item["sublattice"] for item in materials) + 1)


def decimal_oracle(case):
    """Independent 60-digit evaluation, scanning upstream occupancy explicitly."""
    with localcontext() as context:
        context.prec = 60
        zero = Decimal(0)
        one = Decimal(1)
        materials = [
            {key: (value if key == "sublattice" else Decimal(value))
             for key, value in item.items()}
            for item in case["materials"]
        ]
        spins = [[Decimal(value) for value in item["spin"]] for item in case["atoms"]]
        num_cells = sum(map(len, case["stacks"]))
        num_sublattices = case["num_sublattices"]
        groups = [
            [[index for index, item in enumerate(case["atoms"])
              if item["cell"] == cell
              and materials[item["material"]]["sublattice"] == sublattice]
             for sublattice in range(num_sublattices)]
            for cell in range(num_cells)
        ]
        reduced = {}
        for cell in range(num_cells):
            total_count = sum(map(len, groups[cell]))
            for sublattice, members in enumerate(groups[cell]):
                if not members:
                    continue
                selected = [materials[case["atoms"][index]["material"]] for index in members]
                moment = sum((item["moment_muB"] for item in selected), zero)
                magnetization = [
                    sum((spins[index][axis] * item["moment_muB"]
                         for index, item in zip(members, selected)), zero) / moment
                    for axis in range(3)
                ]
                means = {
                    name: sum((item[name] for item in selected), zero) / len(members)
                    for name in ("alpha", "eta", "beta")
                }
                geometry = (Decimal(case["cell_length_m"]) * total_count
                            / Decimal(case["cell_area_m2"]) / len(members) ** 2)
                ordinary = geometry * sum((item["rho_ohm_m"] for item in selected), zero)
                spin_resistance = geometry * sum(
                    (item["rho_spin_ohm_m"] for item in selected), zero
                )
                reduced[cell, sublattice] = (moment, magnetization, means, ordinary, spin_resistance)

        cell_resistance = [zero] * num_cells
        channel_current = [[zero] * num_sublattices for unused in range(num_cells)]
        fields = {}
        stack_resistance = []
        stack_current = []
        for stack in case["stacks"]:
            ordered = stack if case["direction"] == 1 else list(reversed(stack))
            branch_resistance = {}
            upstream = {}
            for position, cell in enumerate(ordered):
                for sublattice in range(num_sublattices):
                    key = (cell, sublattice)
                    if key not in reduced:
                        continue
                    moment, magnetization, means, ordinary, spin_resistance = reduced[key]
                    resistance = ordinary
                    if position:
                        previous = next(
                            candidate for candidate in reversed(ordered[:position])
                            if (candidate, sublattice) in reduced
                        )
                        polarization = reduced[previous, sublattice][1]
                        alignment = sum((left * right for left, right
                                         in zip(magnetization, polarization)), zero)
                        resistance += spin_resistance * (one - alignment) / 2
                        upstream[key] = polarization
                    branch_resistance[key] = resistance
                cell_resistance[cell] = one / sum(
                    (one / branch_resistance[cell, sublattice]
                     for sublattice in range(num_sublattices)
                     if (cell, sublattice) in branch_resistance), zero
                )
            resistance = sum((cell_resistance[cell] for cell in stack), zero)
            current = Decimal(case["voltage_V"]) / resistance
            stack_resistance.append(resistance)
            stack_current.append(current)
            for cell in stack:
                for sublattice in range(num_sublattices):
                    key = (cell, sublattice)
                    if key not in reduced:
                        continue
                    branch_current = current * cell_resistance[cell] / branch_resistance[key]
                    channel_current[cell][sublattice] = branch_current
                    field = [zero, zero, zero]
                    if key in upstream:
                        moment, magnetization, means, ordinary, spin_resistance = reduced[key]
                        polarization = upstream[key]
                        for axis in range(3):
                            next_axis = (axis + 1) % 3
                            last_axis = (axis + 2) % 3
                            crossed = (magnetization[next_axis] * polarization[last_axis]
                                       - magnetization[last_axis] * polarization[next_axis])
                            field[axis] = Decimal("35486911.9121") * branch_current / moment * (
                                (means["eta"] - means["alpha"] * means["beta"]) * crossed
                                + (means["beta"] + means["alpha"] * means["eta"]) * polarization[axis]
                            )
                    fields[key] = field

        atom_fields = []
        derivatives = []
        for index, item in enumerate(case["atoms"]):
            properties = materials[item["material"]]
            field = fields[item["cell"], properties["sublattice"]]
            spin = spins[index]
            damping = properties["alpha"]
            dot = sum((left * right for left, right in zip(spin, field)), zero)
            norm_squared = sum((value * value for value in spin), zero)
            derivative = []
            for axis in range(3):
                next_axis = (axis + 1) % 3
                last_axis = (axis + 2) % 3
                precession = spin[next_axis] * field[last_axis] - spin[last_axis] * field[next_axis]
                damping_term = spin[axis] * dot - field[axis] * norm_squared
                derivative.append(-Decimal("1.760859e11") / (one + damping ** 2)
                                  * (precession + damping * damping_term))
            atom_fields.append(field)
            derivatives.append(derivative)

        def floats(value):
            return [floats(item) for item in value] if isinstance(value, list) else float(value)

        return {key: floats(value) for key, value in dict(
            total_resistance_ohm=one / sum((one / value for value in stack_resistance), zero),
            total_current_A=sum(stack_current, zero), stack_resistance_ohm=stack_resistance,
            stack_current_A=stack_current, cell_resistance_ohm=cell_resistance,
            channel_current_A=channel_current, atom_field_T=atom_fields,
            atom_dspin_dt=derivatives,
        ).items()}


def random_case(seed):
    rng = random.Random(seed)
    num_sublattices = rng.randint(1, 4)
    materials = [
        material(sublattice, rho=10 ** rng.uniform(-8, -5),
                 spin_rho=10 ** rng.uniform(-8, -5), moment=rng.uniform(0.3, 5),
                 alpha=rng.uniform(0, 0.4), eta=rng.uniform(0.05, 0.95),
                 beta=rng.uniform(-0.3, 0.3))
        for sublattice in range(num_sublattices) for unused in range(2)
    ]
    stacks = []
    atoms = []
    next_cell = 0
    for unused in range(rng.randint(1, 3)):
        stack = list(range(next_cell, next_cell + rng.randint(1, 6)))
        next_cell += len(stack)
        stacks.append(stack)
        for cell in stack:
            occupied = list(range(num_sublattices))
            if cell not in (stack[0], stack[-1]):
                occupied = rng.sample(occupied, rng.randint(1, num_sublattices))
            for sublattice in occupied:
                for unused_atom in range(rng.randint(1, 5)):
                    vector = [rng.gauss(0, 1) for unused_axis in range(3)]
                    norm = math.sqrt(sum(value * value for value in vector))
                    atoms.append(atom(cell, 2 * sublattice + rng.randrange(2),
                                      [value / norm for value in vector]))
    rng.shuffle(atoms)
    result = make_case(stacks, materials, atoms, voltage=rng.uniform(0.001, 0.1),
                       direction=rng.choice([-1, 1]))
    result["cell_length_m"] = 10 ** rng.uniform(-10, -8)
    result["cell_area_m2"] = 10 ** rng.uniform(-19, -16)
    return result


class TransportTests(unittest.TestCase):
    def assert_values_close(self, actual, expected, scale=None):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                self.assert_values_close(actual[key], expected[key])
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            if scale is None:
                def leaves(value):
                    if isinstance(value, list):
                        for item in value:
                            yield from leaves(item)
                    else:
                        yield abs(value)
                scale = max(leaves(expected), default=0.0)
            for left, right in zip(actual, expected):
                self.assert_values_close(left, right, scale)
        else:
            self.assertTrue(math.isfinite(actual))
            tolerance = 3e-13 * max(abs(expected), scale or 0.0, 1e-30)
            self.assertLessEqual(abs(actual - expected), tolerance)

    def assert_invariants(self, case, result):
        for stack_index, stack in enumerate(case["stacks"]):
            current = result["stack_current_A"][stack_index]
            entrance = stack[0] if case["direction"] == 1 else stack[-1]
            for cell in stack:
                self.assert_values_close(math.fsum(result["channel_current_A"][cell]), current)
                occupied = {case["materials"][item["material"]]["sublattice"]
                            for item in case["atoms"] if item["cell"] == cell}
                for sublattice, branch in enumerate(result["channel_current_A"][cell]):
                    self.assertGreaterEqual(branch, 0.0)
                    if sublattice not in occupied:
                        self.assertEqual(branch, 0.0)
            for index, item in enumerate(case["atoms"]):
                if item["cell"] == entrance:
                    self.assertEqual(result["atom_field_T"][index], [0.0] * 3)
                    self.assertEqual(result["atom_dspin_dt"][index], [0.0] * 3)
        for item, derivative in zip(case["atoms"], result["atom_dspin_dt"]):
            dot = math.fsum(left * right for left, right in zip(item["spin"], derivative))
            self.assertLessEqual(abs(dot), 1e-14 * max(map(abs, derivative)) + 1e-25)
        self.assert_values_close(result["total_current_A"],
                                 case["voltage_V"] / result["total_resistance_ohm"])

    def test_entrance_parallel_channels(self):
        case = make_case([[0]], [material(0, rho=2), material(1, rho=3)],
                         [atom(0, 0, [0, 0, 1]), atom(0, 1, [1, 0, 0]),
                          atom(0, 0, [0, 1, 0])], voltage=9)
        result = solve(case)
        self.assert_values_close(result["total_resistance_ohm"], 2.25)
        self.assert_values_close(result["channel_current_A"], [[3.0, 1.0]])
        self.assert_invariants(case, result)

    def test_analytical_noncollinear_field_and_derivative(self):
        case = make_case([[0, 1]], [material()],
                         [atom(0, 0, [0, 0, 1]), atom(1, 0, [1, 0, 0])])
        result = solve(case)
        self.assert_values_close(result["cell_resistance_ohm"], [2.0, 4.0])
        self.assert_values_close(result["total_current_A"], 1.0)
        self.assert_values_close(result["atom_field_T"][1],
                                 [0.0, -0.58 * FIELD_FACTOR / 2, 0.26 * FIELD_FACTOR / 2])
        factor = GYROMAGNETIC_RATIO * FIELD_FACTOR / 2 / 1.01
        self.assert_values_close(result["atom_dspin_dt"][1], [0.0, 0.202 * factor, 0.606 * factor])

    def test_parallel_stacks_and_original_ids(self):
        case = make_case([[1], [0]], [material(rho=2), material(rho=4)],
                         [atom(0, 0, [0, 0, 1]), atom(1, 1, [1, 0, 0])], voltage=8)
        result = solve(case)
        self.assert_values_close(result["stack_resistance_ohm"], [4.0, 2.0])
        self.assert_values_close(result["stack_current_A"], [2.0, 4.0])
        self.assert_values_close(result["total_resistance_ohm"], 4.0 / 3.0)

    def test_sparse_memory_and_reversal(self):
        materials = [material(0, rho=1, spin_rho=4, moment=1, alpha=0, eta=1, beta=0),
                     material(1, rho=1, spin_rho=0)]
        atoms = [atom(cell, 1, [0, 0, 1]) for cell in range(5)]
        atoms += [atom(0, 0, [0, 0, 1]), atom(3, 0, [1, 0, 0]), atom(4, 0, [0, 0, -1])]
        case = make_case([list(range(5))], materials, atoms)
        for direction in (1, -1):
            case["direction"] = direction
            result = solve(case)
            self.assert_values_close(result, decimal_oracle(case))
            self.assert_values_close(result["total_resistance_ohm"], 6.0)
            self.assert_values_close(result["channel_current_A"][3], [0.25, 0.75])
            self.assert_values_close(result["atom_field_T"][6], [0, -direction * FIELD_FACTOR / 4, 0])
            self.assert_invariants(case, result)

    def test_zero_reduced_upstream_magnetization(self):
        case = make_case([[0, 1]], [material()],
                         [atom(0, 0, [0, 0, 1]), atom(0, 0, [0, 0, -1]),
                          atom(1, 0, [1, 0, 0])])
        result = solve(case)
        self.assert_values_close(result["total_resistance_ohm"], 6.0)
        self.assertEqual(result["atom_field_T"], [[0.0] * 3] * 3)

    def test_zero_reduced_destination_keeps_longitudinal_field(self):
        case = make_case([[0, 1]], [material()],
                         [atom(0, 0, [0, 0, 1]), atom(1, 0, [1, 0, 0]),
                          atom(1, 0, [-1, 0, 0])])
        result = solve(case)
        self.assert_values_close(result["atom_field_T"][1], [0, 0, FIELD_FACTOR * 0.26 / 4])
        self.assertEqual(result["atom_field_T"][1], result["atom_field_T"][2])
        self.assertNotEqual(result["atom_dspin_dt"][1], [0.0] * 3)
        self.assert_values_close(result, decimal_oracle(case))

    def test_collinear_field_is_not_removed_with_zero_torque(self):
        for orientation, resistance in ((1, 4.0), (-1, 8.0)):
            case = make_case([[0, 1]], [material()],
                             [atom(0, 0, [0, 0, 1]), atom(1, 0, [0, 0, orientation])])
            result = solve(case)
            self.assert_values_close(result["total_resistance_ohm"], resistance)
            self.assertGreater(result["atom_field_T"][1][2], 0)
            self.assertEqual(result["atom_dspin_dt"][1], [0.0] * 3)
            self.assert_values_close(result, decimal_oracle(case))

    def test_unequal_moments_and_atomic_damping(self):
        case = make_case([[0, 1]],
                         [material(moment=1, alpha=0.1), material(moment=3, rho=6, alpha=0.4)],
                         [atom(1, 0, [1, 0, 0]), atom(0, 0, [0, 0, 1]),
                          atom(1, 1, [0, 0, 1])])
        channel = reduce_channels(case, 2)[1][0]
        self.assertEqual(channel.moment_muB, 4.0)
        self.assertEqual(channel.magnetization, [0.25, 0, 0.75])
        self.assertEqual(channel.alpha, 0.25)
        self.assertEqual(channel.ordinary_ohm, 4.0)
        result = solve(case)
        self.assertEqual(result["atom_field_T"][0], result["atom_field_T"][2])
        self.assertNotEqual(result["atom_dspin_dt"][0], result["atom_dspin_dt"][2])
        self.assert_values_close(result, decimal_oracle(case))

    def test_compensated_sublattices_retain_transport(self):
        materials = [material(sublattice, alpha=0, eta=1, beta=0) for sublattice in (0, 1)]
        case = make_case([[0, 1]], materials,
                         [atom(0, 0, [0, 0, 1]), atom(0, 1, [0, 0, -1]),
                          atom(1, 0, [1, 0, 0]), atom(1, 1, [-1, 0, 0])])
        result = solve(case)
        self.assertNotEqual(result["atom_field_T"][2], [0.0] * 3)
        self.assertEqual(result["atom_field_T"][2], result["atom_field_T"][3])
        self.assert_values_close(result, decimal_oracle(case))

    def test_random_high_precision_and_invariants(self):
        for seed in range(32):
            with self.subTest(seed=seed):
                case = random_case(seed)
                result = solve(case)
                self.assert_values_close(result, decimal_oracle(case))
                self.assert_invariants(case, result)

    def test_zero_voltage(self):
        case = random_case(27)
        resistance = solve(case)["total_resistance_ohm"]
        case["voltage_V"] = 0.0
        result = solve(case)
        self.assertEqual(result["total_resistance_ohm"], resistance)
        for key in ("total_current_A", "stack_current_A", "channel_current_A", "atom_field_T", "atom_dspin_dt"):
            def check_zero(value):
                if isinstance(value, list):
                    for item in value:
                        check_zero(item)
                else:
                    self.assertEqual(value, 0.0)
            check_zero(result[key])

    def test_voltage_moment_and_geometry_scaling(self):
        case = random_case(12)
        original = solve(case)
        transformations = [("voltage", 2.0), ("moment", 3.0), ("area", 2.0), ("rho", 4.0)]
        for kind, factor in transformations:
            changed = copy.deepcopy(case)
            if kind == "voltage":
                changed["voltage_V"] *= factor
            elif kind == "area":
                changed["cell_area_m2"] *= factor
            else:
                for item in changed["materials"]:
                    for key in (["moment_muB"] if kind == "moment" else ["rho_ohm_m", "rho_spin_ohm_m"]):
                        item[key] *= factor
            result = solve(changed)
            for key in original:
                resistance_scale = {"voltage": 1, "moment": 1, "area": 1 / factor, "rho": factor}[kind]
                current_scale = {"voltage": factor, "moment": 1, "area": factor, "rho": 1 / factor}[kind]
                scale = (resistance_scale if "resistance" in key else current_scale)
                if key in ("atom_field_T", "atom_dspin_dt") and kind == "moment":
                    scale = 1 / factor
                def scaled(value):
                    return [scaled(item) for item in value] if isinstance(value, list) else value * scale
                self.assert_values_close(result[key], scaled(original[key]))

    def test_atom_order_and_rotational_covariance(self):
        case = random_case(17)
        original = solve(case)
        case["atoms"].reverse()
        reordered = solve(case)
        for key in original:
            expected = list(reversed(original[key])) if key.startswith("atom_") else original[key]
            self.assert_values_close(reordered[key], expected)
        for item in case["atoms"]:
            item["spin"] = item["spin"][1:] + item["spin"][:1]
        rotated = solve(case)
        for key in reordered:
            expected = ([vector[1:] + vector[:1] for vector in reordered[key]]
                        if key.startswith("atom_") else reordered[key])
            self.assert_values_close(rotated[key], expected)

    def test_cli(self):
        case = random_case(9)
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary) / "case.json"
            destination = Path(temporary) / "output.json"
            source.write_text(json.dumps(case), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "solve.py"), str(source), str(destination)],
                           check=True, timeout=20)
            result = json.loads(destination.read_text(encoding="utf-8"))
        self.assert_values_close(result, decimal_oracle(case))

    @unittest.skipUnless(os.environ.get("TRANSPORT_EXAMPLES"), "public example directory not specified")
    def test_public_examples(self):
        paths = sorted(Path(os.environ["TRANSPORT_EXAMPLES"]).glob("example*.json"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            with self.subTest(path=path.name):
                case = json.loads(path.read_text(encoding="utf-8"))
                result = solve(case)
                self.assert_values_close(result, decimal_oracle(case))
                self.assert_invariants(case, result)


if __name__ == "__main__":
    unittest.main()
