"""Resolved multisublattice transport under the version-1 input contract."""

import json
import math
import sys
from typing import NamedTuple


FIELD_FACTOR = 35486911.9121
GYROMAGNETIC_RATIO = 1.760859e11


class Channel(NamedTuple):
    moment_muB: float
    magnetization: list[float]
    ordinary_ohm: float
    spin_ohm: float
    alpha: float
    eta: float
    beta: float


def cross(left, right):
    return [
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    ]


def reduce_channels(case, num_cells):
    groups = [
        [[] for unused in range(case["num_sublattices"])]
        for unused in range(num_cells)
    ]
    for atom in case["atoms"]:
        material = case["materials"][atom["material"]]
        groups[atom["cell"]][material["sublattice"]].append(
            (atom["spin"], material)
        )

    channels = []
    for cell_groups in groups:
        cell_count = sum(map(len, cell_groups))
        cell_channels = []
        for members in cell_groups:
            if not members:
                cell_channels.append(None)
                continue
            count = len(members)
            moment = math.fsum(material["moment_muB"] for spin, material in members)
            magnetization = [
                math.fsum(
                    material["moment_muB"] * spin[axis]
                    for spin, material in members
                ) / moment
                for axis in range(3)
            ]
            means = [
                math.fsum(material[name] for spin, material in members) / count
                for name in ("rho_ohm_m", "rho_spin_ohm_m", "alpha", "eta", "beta")
            ]
            geometry = case["cell_length_m"] / (
                (count / cell_count) * case["cell_area_m2"]
            )
            cell_channels.append(Channel(
                moment, magnetization, means[0] * geometry, means[1] * geometry,
                means[2], means[3], means[4],
            ))
        channels.append(cell_channels)
    return channels


def solve(case):
    num_cells = sum(map(len, case["stacks"]))
    num_sublattices = case["num_sublattices"]
    channels = reduce_channels(case, num_cells)
    conductance = [[0.0] * num_sublattices for unused in range(num_cells)]
    channel_current = [[0.0] * num_sublattices for unused in range(num_cells)]
    channel_field = [
        [[0.0, 0.0, 0.0] for unused in range(num_sublattices)]
        for unused in range(num_cells)
    ]
    cell_resistance = [0.0] * num_cells
    stack_resistance = []
    stack_current = []

    for stack in case["stacks"]:
        upstream = [None] * num_sublattices
        for cell in stack[::case["direction"]]:
            for sublattice, channel in enumerate(channels[cell]):
                if channel is None:
                    continue
                resistance = channel.ordinary_ohm
                polarization = upstream[sublattice]
                if polarization is not None:
                    alignment = math.fsum(
                        current * previous
                        for current, previous in zip(channel.magnetization, polarization)
                    )
                    resistance += 0.5 * channel.spin_ohm * (1.0 - alignment)
                    crossed = cross(channel.magnetization, polarization)
                    transverse = channel.eta - channel.alpha * channel.beta
                    longitudinal = channel.beta + channel.alpha * channel.eta
                    channel_field[cell][sublattice] = [
                        transverse * crossed[axis] + longitudinal * polarization[axis]
                        for axis in range(3)
                    ]
                conductance[cell][sublattice] = 1.0 / resistance
                upstream[sublattice] = channel.magnetization
            cell_resistance[cell] = 1.0 / math.fsum(conductance[cell])

        resistance = math.fsum(cell_resistance[cell] for cell in stack)
        current = case["voltage_V"] / resistance
        stack_resistance.append(resistance)
        stack_current.append(current)
        for cell in stack:
            voltage_drop = current * cell_resistance[cell]
            for sublattice, channel in enumerate(channels[cell]):
                if channel is None:
                    continue
                branch_current = voltage_drop * conductance[cell][sublattice]
                channel_current[cell][sublattice] = branch_current
                factor = FIELD_FACTOR * (branch_current / channel.moment_muB)
                channel_field[cell][sublattice] = [
                    factor * component for component in channel_field[cell][sublattice]
                ]

    atom_field = []
    atom_derivative = []
    for atom in case["atoms"]:
        material = case["materials"][atom["material"]]
        field = channel_field[atom["cell"]][material["sublattice"]]
        atom_field.append(field)
        first_cross = cross(atom["spin"], field)
        second_cross = cross(atom["spin"], first_cross)
        damping = material["alpha"]
        factor = -GYROMAGNETIC_RATIO / (1.0 + damping * damping)
        atom_derivative.append([
            factor * (first_cross[axis] + damping * second_cross[axis])
            for axis in range(3)
        ])

    return {
        "total_resistance_ohm": 1.0 / math.fsum(
            1.0 / resistance for resistance in stack_resistance
        ),
        "total_current_A": math.fsum(stack_current),
        "stack_resistance_ohm": stack_resistance,
        "stack_current_A": stack_current,
        "cell_resistance_ohm": cell_resistance,
        "channel_current_A": channel_current,
        "atom_field_T": atom_field,
        "atom_dspin_dt": atom_derivative,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python solve.py CASE.json OUTPUT.json")
    with open(sys.argv[1], encoding="utf-8") as source:
        case = json.load(source)
    result = solve(case)
    with open(sys.argv[2], "w", encoding="utf-8") as destination:
        json.dump(result, destination, allow_nan=False, separators=(",", ":"))
        destination.write("\n")


if __name__ == "__main__":
    main()
