import argparse
import ctypes
import hashlib
import itertools
import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
PAIRS = list(itertools.combinations(range(5), 2))
FAMILIES = ["generic", "soft", "collinear", "double_collinear", "triple_collinear"]


def prepare_native():
    source_path = ROOT / "research/releases/src/Zqq/treeZQ.f"
    source = source_path.read_text()
    first = source.index("      function A345(")
    last = source.index("      function A345p(")
    source = source[first:last]
    native = CONCEPT / "adversary/native"
    native.mkdir(parents=True, exist_ok=True)
    for precision in (8, 16):
        kernel = source.replace("real*8", "real*" + str(precision))
        if precision == 16:
            kernel = re.sub(r"([0-9.])d([+-]?\d+)", r"\1q\2", kernel)
        kernel_path = native / f"kernel{precision}.f"
        kernel_path.write_text(kernel)
        wrapper = f"""subroutine kernel_batch(count, inputs, outputs) bind(C)
use iso_c_binding
implicit none
integer(c_int), value :: count
real(c_double), intent(in) :: inputs(10,count)
real(c_double), intent(out) :: outputs(count)
real({precision}) :: values(10), forward, backward
real({precision}), external :: A345
integer :: sample
do sample = 1,count
  values = real(inputs(:,sample),{precision})
  forward = A345(values(1),values(2),values(3),values(4), &
       values(5),values(6),values(7),values(8),values(9),values(10))
  backward = A345(values(1),values(4),values(3),values(2), &
       values(7),values(6),values(5),values(10),values(9),values(8))
  outputs(sample) = real((forward+backward)/2,c_double)
end do
end subroutine
"""
        wrapper_path = native / f"wrapper{precision}.f90"
        wrapper_path.write_text(wrapper)
        subprocess.run(["gfortran", "-O2", "-fPIC", "-shared", str(kernel_path),
                        str(wrapper_path), "-o", str(native / f"kernel{precision}.so")], check=True)
    return native


def native_values(invariants, native, precision=16):
    library = ctypes.CDLL(str(native / f"kernel{precision}.so"))
    function = library.kernel_batch
    pointer = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [ctypes.c_int, pointer, pointer]
    inputs = np.ascontiguousarray(invariants, dtype=np.float64)
    outputs = np.empty(len(inputs), dtype=np.float64)
    function(len(inputs), inputs.ctypes.data_as(pointer), outputs.ctypes.data_as(pointer))
    return outputs


def unit_directions(generator, count):
    directions = generator.normal(size=(count, 5, 3))
    return directions / np.linalg.norm(directions, axis=2, keepdims=True)


def generate_events(generator, count, family):
    directions = unit_directions(generator, count)
    energies = generator.gamma(2.0, 1.0, size=(count, 5))
    angle = 10.0 ** generator.uniform(-2.5, -0.35, size=(count, 1))
    if family == "soft":
        energies[:, 3] *= 10.0 ** generator.uniform(-4.5, -1.0, count)
    if family in ("collinear", "double_collinear", "triple_collinear"):
        directions[:, 3] = directions[:, 2] + angle * directions[:, 3]
        directions[:, 3] /= np.linalg.norm(directions[:, 3], axis=1, keepdims=True)
    if family == "double_collinear":
        second_angle = 10.0 ** generator.uniform(-2.5, -0.35, size=(count, 1))
        directions[:, 4] = directions[:, 0] + second_angle * directions[:, 4]
        directions[:, 4] /= np.linalg.norm(directions[:, 4], axis=1, keepdims=True)
    if family == "triple_collinear":
        second_angle = 10.0 ** generator.uniform(-2.5, -0.35, size=(count, 1))
        directions[:, 4] = directions[:, 2] + second_angle * directions[:, 4]
        directions[:, 4] /= np.linalg.norm(directions[:, 4], axis=1, keepdims=True)
    momenta = energies[:, :, None] * directions
    total_energy = np.sum(energies, axis=1)
    total_vector = np.sum(momenta, axis=1)
    velocity = total_vector / total_energy[:, None]
    beta_squared = np.sum(velocity * velocity, axis=1)
    gamma = 1.0 / np.sqrt(1.0 - beta_squared)
    projection = np.einsum("nkj,nj->nk", momenta, velocity)
    factor = (gamma * gamma / (gamma + 1.0))[:, None] * projection - gamma[:, None] * energies
    boosted = momenta + factor[:, :, None] * velocity[:, None, :]
    boosted_energy = np.linalg.norm(boosted, axis=2)
    normalization = np.sum(boosted_energy, axis=1)
    boosted /= normalization[:, None, None]
    boosted_energy /= normalization[:, None]
    unit = boosted / boosted_energy[:, :, None]
    invariants = np.stack([boosted_energy[:, left] * boosted_energy[:, right] *
                           np.sum((unit[:, left] - unit[:, right]) ** 2, axis=1)
                           for left, right in PAIRS], axis=1)
    four_momenta = np.concatenate([boosted, boosted_energy[:, :, None]], axis=2)
    return invariants, four_momenta


def generate_split(generator, per_family, native):
    all_invariants, all_momenta, all_labels, all_families = [], [], [], []
    rejected = {}
    for family_index, family in enumerate(FAMILIES):
        accepted = 0
        rejected[family] = 0
        while accepted < per_family:
            count = per_family - accepted
            invariants, momenta = generate_events(generator, count, family)
            raw = native_values(invariants, native)
            keep = np.isfinite(raw) & (raw > 0) & (invariants.min(axis=1) > 1e-10)
            rejected[family] += int(np.sum(~keep))
            all_invariants.append(invariants[keep])
            all_momenta.append(momenta[keep])
            all_labels.append(np.log(raw[keep]))
            all_families.append(np.full(int(np.sum(keep)), family_index, dtype=np.int64))
            accepted += int(np.sum(keep))
    invariants = np.concatenate(all_invariants)
    momenta = np.concatenate(all_momenta)
    labels = np.concatenate(all_labels)
    families = np.concatenate(all_families)
    order = generator.permutation(len(labels))
    return {"s": invariants[order], "p": momenta[order], "log_weight": labels[order],
            "family": families[order]}, rejected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-per-family", type=int, default=5000)
    parser.add_argument("--test-per-family", type=int, default=1200)
    arguments = parser.parse_args()
    started = time.monotonic()
    native = prepare_native()
    manifest = {"source": "official EERAD3 2.0.0, treeZQ.f A345; sig5ZQ tt0",
                "source_sha256": hashlib.sha256((ROOT / "research/releases/src/Zqq/treeZQ.f").read_bytes()).hexdigest(),
                "families": FAMILIES, "rejections": {}}
    destinations = [("train", arguments.train_per_family, 928421, CONCEPT / "participant/input"),
                    ("validation", 300, 938784, CONCEPT / "participant/input"),
                    ("test", arguments.test_per_family, 583102048, CONCEPT / "evaluator/hidden")]
    for name, size, seed, destination in destinations:
        data, rejected = generate_split(np.random.default_rng(seed), size, native)
        np.savez_compressed(destination / f"{name}.npz", **data)
        manifest["rejections"][name] = rejected
        manifest[name] = {"size": len(data["s"]), "seed": seed}
        selected = np.arange(min(len(data["s"]), 1200))
        double = native_values(data["s"][selected], native, 8)
        quad = np.exp(data["log_weight"][selected])
        relative = np.abs(double - quad) / quad
        manifest[name]["double_quad_max_relative"] = float(relative.max())
        manifest[name]["cm_residual"] = float(np.abs(data["p"][:, :, :3].sum(axis=1)).max())
        manifest[name]["invariant_sum_residual"] = float(np.abs(data["s"].sum(axis=1) - 1).max())
        print(name, manifest[name], flush=True)
    manifest["wall_seconds"] = time.monotonic() - started
    (CONCEPT / "adversary/data_provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
