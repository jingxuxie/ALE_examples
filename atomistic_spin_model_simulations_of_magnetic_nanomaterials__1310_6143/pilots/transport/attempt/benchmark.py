"""Generate and validate a maximum-size case under a 1 GiB address-space cap."""

import argparse
import json
import math
from pathlib import Path
import resource
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def maximum_case(direction):
    stacks = [list(range(32 * stack, 32 * (stack + 1))) for stack in range(16)]
    materials = [
        dict(sublattice=index // 8, rho_ohm_m=10 ** (-8 + 3 * index / 63),
             rho_spin_ohm_m=10 ** (-8 + 3 * ((17 * index) % 64) / 63),
             moment_muB=0.5 + index / 16, alpha=0.005 + index / 256,
             eta=0.1 + index / 96, beta=-0.2 + index / 160)
        for index in range(64)
    ]
    groups = []
    for stack in stacks:
        for cell in stack:
            occupied = (list(range(8)) if cell in (stack[0], stack[-1])
                        else [(cell + offset) % 8 for offset in range(1 + cell % 8)])
            groups.extend((cell, sublattice) for sublattice in occupied)
    atoms = []
    for index in range(50000):
        cell, sublattice = groups[index % len(groups)]
        azimuth = 0.013 * cell + 0.37 * sublattice + 0.019 * (index // len(groups))
        polar = 0.1 + 0.047 * ((cell + sublattice + index // len(groups)) % 61)
        spin = [math.sin(polar) * math.cos(azimuth), math.sin(polar) * math.sin(azimuth),
                math.cos(polar)]
        atoms.append(dict(cell=cell, material=8 * sublattice + (index // len(groups)) % 8,
                          spin=spin))
    return dict(version=1, case_id="maximum_size_synthetic", num_sublattices=8,
                voltage_V=0.07, direction=direction, cell_length_m=1.7e-9,
                cell_area_m2=8.3e-18, stacks=stacks, materials=materials, atoms=atoms)


def validate(case, result):
    shapes = dict(stack_resistance_ohm=(16,), stack_current_A=(16,),
                  cell_resistance_ohm=(512,), channel_current_A=(512, 8),
                  atom_field_T=(50000, 3), atom_dspin_dt=(50000, 3))

    def check_shape(value, shape):
        if shape:
            assert isinstance(value, list) and len(value) == shape[0]
            for item in value:
                check_shape(item, shape[1:])
        else:
            assert math.isfinite(value)

    assert set(result) == set(shapes) | {"total_resistance_ohm", "total_current_A"}
    for key, shape in shapes.items():
        check_shape(result[key], shape)
    assert math.isfinite(result["total_resistance_ohm"])
    assert math.isfinite(result["total_current_A"])
    entrances = {stack[0] if case["direction"] == 1 else stack[-1] for stack in case["stacks"]}
    occupied = {(item["cell"], case["materials"][item["material"]]["sublattice"])
                for item in case["atoms"]}
    conservation_error = 0.0
    for stack_index, stack in enumerate(case["stacks"]):
        current = result["stack_current_A"][stack_index]
        for cell in stack:
            conservation_error = max(conservation_error,
                                     abs(math.fsum(result["channel_current_A"][cell]) / current - 1))
            for sublattice, branch in enumerate(result["channel_current_A"][cell]):
                assert branch >= 0
                if (cell, sublattice) not in occupied:
                    assert branch == 0
    tangent_error = 0.0
    for index, item in enumerate(case["atoms"]):
        derivative = result["atom_dspin_dt"][index]
        if item["cell"] in entrances:
            assert derivative == [0.0] * 3
            assert result["atom_field_T"][index] == [0.0] * 3
        norm = math.hypot(*derivative)
        if norm:
            tangent_error = max(tangent_error, abs(math.fsum(
                left * right for left, right in zip(item["spin"], derivative)
            )) / norm)
    assert conservation_error < 1e-14
    assert tangent_error < 1e-14
    return dict(max_relative_current_conservation_error=conservation_error,
                max_relative_tangency_error=tangent_error)


def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", type=int, choices=(-1, 1), default=-1)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "validation")
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    source = arguments.output_dir / "maximum_case.json"
    destination = arguments.output_dir / "maximum_output.json"
    timing = arguments.output_dir / "timing.json"
    case = maximum_case(arguments.direction)
    with source.open("w", encoding="utf-8") as handle:
        json.dump(case, handle, separators=(",", ":"), allow_nan=False)
    subprocess.run(
        ["/usr/bin/time", "-f", '{"elapsed_seconds":%e,"peak_rss_kib":%M}',
         "-o", str(timing), sys.executable, str(ROOT / "solve.py"),
         str(source), str(destination)],
        check=True, timeout=25, preexec_fn=limit_memory,
    )
    with destination.open(encoding="utf-8") as handle:
        result = json.load(handle)
    metrics = json.loads(timing.read_text(encoding="utf-8"))
    assert metrics["elapsed_seconds"] < 20
    metrics.update(validate(case, result))
    metrics["direction"] = arguments.direction
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
