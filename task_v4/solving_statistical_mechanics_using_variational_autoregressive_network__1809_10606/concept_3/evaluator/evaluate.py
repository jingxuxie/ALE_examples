"""Trusted artifact-only evaluator. Launch with python -I; never import a submission."""

import argparse
import ast
import io
import json
import os
from pathlib import Path
import stat
import struct
import zipfile

import numpy as np


TARGETS = {"mean_forward_kl": 0.02, "worst_family_mean_kl": 0.035, "max_tv": 0.12}
MAX_ARTIFACT_BYTES = 65536
FAMILIES = ("interpolation", "cooling", "fields")
HIDDEN = Path(__file__).resolve().parent / "hidden"


def _array(payload, expected_shape, expected_descr):
    stream = io.BytesIO(payload)
    if stream.read(6) != b"\x93NUMPY":
        raise ValueError("not an NPY array")
    version = stream.read(2)
    if version == b"\x01\x00":
        width, encoding = 2, "latin1"
    elif version == b"\x02\x00":
        width, encoding = 4, "latin1"
    else:
        raise ValueError("only NPY versions 1 and 2 are accepted")
    length_bytes = stream.read(width)
    if len(length_bytes) != width:
        raise ValueError("truncated NPY header")
    length = struct.unpack("<H" if width == 2 else "<I", length_bytes)[0]
    if not 1 <= length <= 2048:
        raise ValueError("NPY header too large")
    header_bytes = stream.read(length)
    if len(header_bytes) != length:
        raise ValueError("truncated NPY header")
    header = ast.literal_eval(header_bytes.decode(encoding))
    if not isinstance(header, dict) or set(header) != {"descr", "fortran_order", "shape"}:
        raise ValueError("invalid NPY header schema")
    if header["descr"] != expected_descr or header["fortran_order"] is not False:
        raise ValueError("invalid array dtype or layout")
    if header["shape"] != expected_shape or any(type(dimension) is not int for dimension in header["shape"]):
        raise ValueError("invalid array shape")
    body = stream.read()
    dtype = np.dtype(expected_descr)
    if len(body) != int(np.prod(expected_shape)) * dtype.itemsize:
        raise ValueError("invalid NPY payload length")
    return np.frombuffer(body, dtype=dtype).reshape(expected_shape).copy()


def load_predictions(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("symlink artifact rejected")
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= MAX_ARTIFACT_BYTES:
            raise ValueError("artifact must be a regular file of at most 65536 bytes")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            payload = handle.read(MAX_ARTIFACT_BYTES + 1)
        if len(payload) != metadata.st_size:
            raise ValueError("artifact changed while reading")
    finally:
        os.close(descriptor)
    expected = {"probabilities.npy": ((24, 64), "<f8"), "query_ids.npy": ((24,), "<U24")}
    arrays = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if len(members) != 2 or {member.filename for member in members} != set(expected):
            raise ValueError("archive must contain exactly probabilities.npy and query_ids.npy")
        for member in members:
            if member.flag_bits & 1 or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError("unsupported ZIP member")
            if member.file_size > 16384 or member.file_size < 1:
                raise ValueError("oversized or empty ZIP member")
            with archive.open(member) as handle:
                member_payload = handle.read(16385)
            if len(member_payload) != member.file_size:
                raise ValueError("invalid ZIP member size")
            arrays[member.filename[:-4]] = _array(member_payload, *expected[member.filename])
    probabilities = arrays["probabilities"]
    if not np.isfinite(probabilities).all() or np.any(probabilities <= 0) or np.any(probabilities > 1):
        raise ValueError("probabilities must be finite and strictly positive")
    if np.any(np.abs(probabilities.sum(axis=1) - 1.0) > 1e-10):
        raise ValueError("each probability row must sum to one within 1e-10")
    return probabilities, arrays["query_ids"], len(payload)


def score_arrays(truth, predictions, families):
    normalized = predictions / predictions.sum(axis=1, keepdims=True)
    divergence = np.maximum(0.0, np.sum(truth * (np.log(truth) - np.log(normalized)), axis=1))
    variation = 0.5 * np.sum(np.abs(truth - normalized), axis=1)
    family_means = {family: float(divergence[np.asarray(families) == family].mean()) for family in FAMILIES}
    metrics = {"mean_forward_kl": float(divergence.mean()),
               "worst_family_mean_kl": max(family_means.values()), "max_tv": float(variation.max())}
    return metrics, family_means, divergence, variation


def evaluate(submission, private_dir=HIDDEN):
    try:
        submission = Path(submission)
        if submission.is_symlink():
            raise ValueError("symlink submission rejected")
        artifact = submission / "predictions.npz" if submission.is_dir() else submission
        predictions, query_ids, byte_count = load_predictions(artifact)
        with np.load(Path(private_dir) / "labels.npz", allow_pickle=False) as labels:
            truth = labels["probabilities"]
            expected_ids = labels["query_ids"]
        families = json.loads((Path(private_dir) / "scoring.json").read_text())["families"]
        if not np.array_equal(query_ids, expected_ids):
            raise ValueError("query IDs must exactly match the published order")
        if truth.shape != (24, 64) or not np.isfinite(truth).all() or np.any(truth <= 0):
            raise ValueError("invalid reference")
        if not np.allclose(truth.sum(axis=1), 1.0, atol=1e-12, rtol=0):
            raise ValueError("invalid reference normalization")
        if len(families) != 24 or any(families.count(family) != 8 for family in FAMILIES):
            raise ValueError("invalid family configuration")
        metrics, family_means, divergence, variation = score_arrays(truth, predictions, families)
        passed = all(metrics[name] <= bound for name, bound in TARGETS.items())
        return {"valid": True, "passed": bool(passed), "reason": "passed" if passed else "quality target not met",
                "core_score": 1.0 / (1.0 + metrics["mean_forward_kl"]),
                "worst_family_score": 1.0 / (1.0 + metrics["worst_family_mean_kl"]),
                "runtime_resource_score": 1.0 - byte_count / MAX_ARTIFACT_BYTES,
                "metrics": metrics, "family_mean_kl": family_means,
                "per_query_kl": divergence.tolist(), "per_query_tv": variation.tolist(),
                "targets": TARGETS, "resource": {"valid": True, "artifact_bytes": byte_count,
                                                   "max_artifact_bytes": MAX_ARTIFACT_BYTES}}
    except Exception as error:
        return {"valid": False, "passed": False, "reason": "invalid artifact or reference: " + type(error).__name__,
                "core_score": 0.0, "worst_family_score": 0.0, "runtime_resource_score": 0.0,
                "targets": TARGETS, "resource": {"valid": False}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.submission)
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(serialized, end="")
    raise SystemExit(0 if result["valid"] else 2)


if __name__ == "__main__":
    main()
