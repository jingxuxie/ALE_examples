import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import warnings

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def serialize(instance):
    rows = [" ".join(map(str, [instance["detectors"], len(instance["taps"]),
                             instance["budget"], len(instance["regimes"]),
                             len(instance["channels"])])),
            " ".join(map(str, instance["taps"]))]
    for channel in instance["channels"]:
        rows.append(str(len(channel["signatures"])))
        rows.append(" ".join(map(str, channel["signatures"])))
        rows.extend(" ".join(map(str, probabilities)) for probabilities in channel["probabilities"])
    return "\n".join(rows) + "\n"


def compress_instance(instance):
    signatures = [signature for channel in instance["channels"] for signature in channel["signatures"]]
    basis = {}
    vectors = []
    taps = []
    for tap in instance["taps"]:
        image = sum(((tap & signature).bit_count() & 1) << branch
                    for branch, signature in enumerate(signatures))
        coordinates = 0
        while image:
            pivot = image.bit_length() - 1
            if pivot in basis:
                vector, coefficient = basis[pivot]
                image ^= vector
                coordinates ^= coefficient
            else:
                coefficient = 1 << len(vectors)
                basis[pivot] = image, coefficient
                vectors.append(image)
                coordinates ^= coefficient
                break
        taps.append(coordinates)
    rank = len(vectors)
    channels = []
    branch = 0
    for original in instance["channels"]:
        projected = []
        for signature in original["signatures"]:
            value = (signature >> instance["detectors"]) << rank
            value |= sum(((vector >> branch) & 1) << position
                         for position, vector in enumerate(vectors))
            projected.append(value)
            branch += 1
        channels.append({"signatures": projected, "probabilities": original["probabilities"]})
    return dict(instance, detectors=rank, taps=taps, channels=channels)


def marginals(instance, selected):
    import numpy as np
    width = len(selected)
    size = 1 << (width + 1)
    distribution = np.zeros((len(instance["regimes"]), size))
    distribution[:, 0] = 1
    indices = np.arange(size)
    for channel in instance["channels"]:
        probabilities = np.asarray(channel["probabilities"])
        updated = distribution * (1 - probabilities.sum(axis=1))[:, None]
        for branch, signature in enumerate(channel["signatures"]):
            projected = (signature >> instance["detectors"]) << width
            for position, tap in enumerate(selected):
                projected |= ((signature & instance["taps"][tap]).bit_count() & 1) << position
            updated += distribution[:, indices ^ projected] * probabilities[:, branch, None]
        distribution = updated
    return distribution.reshape(len(instance["regimes"]), 2, 1 << width).transpose(0, 2, 1)


def improve_tables(instance, candidates, deadline, engine=None):
    import numpy as np
    from scipy.optimize import linprog
    warnings.filterwarnings("ignore", message="Unrecognized options detected.*")
    warnings.filterwarnings("ignore", message="Unknown solver options.*")

    candidates.sort(key=lambda answer: answer["score"])
    best = candidates[0]
    best_score = best["score"]
    promising = []
    for answer in candidates:
        if time.monotonic() > deadline - 0.4:
            break
        distribution = marginals(instance, answer["selected"])
        difference = distribution[:, :, 0] - distribution[:, :, 1]
        constant = distribution[:, :, 1].sum(axis=1)
        table = np.asarray(answer["correction"], dtype=float)
        score = float(np.max(constant + difference @ table))
        answer = {"selected": answer["selected"], "correction": answer["correction"]}
        if score < best_score:
            best_score, best = score, answer
        fixed_one = np.all(difference <= 0, axis=0)
        active = np.any(difference < 0, axis=0) & np.any(difference > 0, axis=0)
        base = constant + difference[:, fixed_one].sum(axis=1)
        reduced = difference[:, active]
        objective = np.zeros(reduced.shape[1] + 1)
        objective[-1] = 1
        constraints = np.column_stack((reduced, -np.ones(len(base))))
        relaxation = linprog(objective, A_ub=constraints, b_ub=-base,
                             bounds=[(0, 1)] * reduced.shape[1] + [(0, 1)],
                             method="highs", options={"presolve": True, "threads": 1})
        if relaxation.success and relaxation.fun < best_score - 1e-9:
            rounded = fixed_one.astype(float)
            rounded[active] = np.round(relaxation.x[:-1])
            fractional = np.flatnonzero((relaxation.x[:-1] > 1e-7) &
                                        (relaxation.x[:-1] < 1 - 1e-7))
            if 0 < len(fractional) <= 10:
                choices = np.arange(1 << len(fractional))[:, None]
                assignments = (choices >> np.arange(len(fractional))) & 1
                active_table = rounded[active]
                active_table[fractional] = 0
                trial_risks = (base + reduced @ active_table)[:, None]
                trial_risks = trial_risks + reduced[:, fractional] @ assignments.T
                active_table[fractional] = assignments[np.argmin(trial_risks.max(axis=0))]
                rounded[active] = active_table
            rounded_score = float(np.max(constant + difference @ rounded))
            if rounded_score < score:
                score = rounded_score
                answer = {"selected": answer["selected"], "correction": rounded.astype(int).tolist()}
            if score < best_score:
                best_score, best = score, answer
            weights = np.maximum(-relaxation.ineqlin.marginals, 0)
            weights /= weights.sum()
            promising.append((relaxation.fun, answer, constant, difference, weights))
    promising.sort(key=lambda item: item[0])
    if engine is None:
        engine = Path(__file__).resolve().parent / "engine"
    remaining = deadline - time.monotonic()
    if promising and remaining > 0.15:
        rows = [str(len(promising))]
        for lower, answer, constant, difference, weights in promising:
            rows.append(f"{len(constant)} {difference.shape[1]}")
            rows.append(" ".join(map(str, constant)))
            rows.extend(" ".join(map(str, column)) for column in difference.T)
            rows.append(" ".join(map(str, weights)))
            rows.append(" ".join(map(str, answer["correction"])))
        process = subprocess.run([str(engine), "tables", str(max(0.05, remaining - 0.08))],
                                 input="\n".join(rows) + "\n", text=True,
                                 stdout=subprocess.PIPE, check=True)
        polished = json.loads(process.stdout)
        selected = promising[polished["candidate"]][1]["selected"]
        proposal = {"selected": selected, "correction": polished["correction"]}
        distribution = marginals(instance, selected)
        table = np.asarray(proposal["correction"], dtype=int)
        score = distribution[:, np.arange(len(table)), 1 - table].sum(axis=1).max()
        if score < best_score:
            best = proposal
    return {"selected": best["selected"], "correction": best["correction"]}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, default=40.5)
    arguments = parser.parse_args()
    instance = json.loads(Path(arguments.input).read_text())
    correlations = [1.0] * len(instance["regimes"])
    for channel in instance["channels"]:
        for regime, probabilities in enumerate(channel["probabilities"]):
            probability = sum(probability for signature, probability in
                              zip(channel["signatures"], probabilities)
                              if signature >> instance["detectors"])
            correlations[regime] *= 1 - 2 * probability
    constant = int(max((1 + value) * 0.5 for value in correlations) <
                   max((1 - value) * 0.5 for value in correlations))
    answer = {"selected": [], "correction": [constant]}
    Path(arguments.output).write_text(json.dumps(answer) + "\n")
    root = Path(__file__).resolve().parent
    engine = root / "engine"
    temporary = None
    data = serialize(compress_instance(instance))
    process = None
    for attempt in range(2):
        try:
            if not engine.exists() or attempt:
                if temporary is not None:
                    temporary.cleanup()
                temporary = tempfile.TemporaryDirectory(prefix="detector_decoder_",
                                                         dir=Path(arguments.output).resolve().parent)
                engine = Path(temporary.name) / "engine"
                subprocess.run(["g++", "-std=c++17", "-O3", "-march=native", str(root / "engine.cpp"),
                                "-o", str(engine)], check=True, timeout=10)
            remaining = arguments.seconds - (time.monotonic() - started)
            search_seconds = max(0.1, remaining - min(6.0, remaining * 0.18))
            process = subprocess.run([str(engine), str(search_seconds)], input=data, text=True,
                                     stdout=subprocess.PIPE, check=True,
                                     timeout=max(0.2, remaining + 1.0))
            break
        except subprocess.TimeoutExpired:
            print("Search reached its safety timeout.", file=sys.stderr)
            return
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"Rebuilding search engine: {error}", file=sys.stderr)
    if process is None:
        return
    candidates = json.loads(process.stdout)
    candidates.sort(key=lambda answer: answer["score"])
    answer = {key: candidates[0][key] for key in ("selected", "correction")}
    Path(arguments.output).write_text(json.dumps(answer) + "\n")
    try:
        answer = improve_tables(instance, candidates, started + arguments.seconds, engine)
    except Exception as error:
        print(f"Decoder polishing unavailable: {error}", file=sys.stderr)
    Path(arguments.output).write_text(json.dumps(answer) + "\n")
    if temporary is not None:
        temporary.cleanup()


if __name__ == "__main__":
    main()
