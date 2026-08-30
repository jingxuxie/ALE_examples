"""Bounded sidecar training; no evaluator-private data are opened."""

import itertools
import json
import os
from pathlib import Path
import resource
import sys
import time


ROOT = Path(__file__).resolve().parent
for name in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
for name, directory in (("HOME", ".home"), ("TMPDIR", ".tmp"), ("TORCHINDUCTOR_CACHE_DIR", ".cache")):
    location = ROOT / directory
    location.mkdir(exist_ok=True)
    os.environ[name] = str(location)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
resource.setrlimit(resource.RLIMIT_CPU, (1000, 1005))

import numpy as np
import torch


torch.set_num_threads(1)
torch.set_num_interop_threads(1)
PUBLIC = ROOT.parents[1] / "participant" / "input"
sys.path.insert(0, str(PUBLIC))
import generator
from solve import coordinates, network_prediction, predict


def cpu():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def metrics(prediction, targets, families):
    errors = []
    for index, family in enumerate(families):
        bands = 3 if family == 3 else 2
        errors.append(min(float(np.sqrt(np.mean(((prediction[index, :bands] - targets[index, list(order)]) / generator.MASS_SCALES) ** 2)))
                          for order in itertools.permutations(range(bands))))
    errors = np.asarray(errors)
    grouped = {generator.FAMILIES[family]: float(errors[families == family].mean())
               for family in range(4) if np.any(families == family)}
    core, worst, tail = float(errors.mean()), max(grouped.values()), float(np.quantile(errors, .9))
    return dict(core=core, worst=worst, case_p90=tail, families=grouped,
                objective=max(core, worst / 1.25, tail / 1.75),
                passed=core <= 1 and worst <= 1.25 and tail <= 1.75)


def simulate():
    random = np.random.default_rng(51829473)
    maximum = 48000
    families = random.choice(4, maximum, p=[1 / 6, 1 / 6, 1 / 6, .5])
    clean = np.empty((maximum, 2, 2, len(generator.OMEGA)), dtype=np.float32)
    targets = np.empty((maximum, 3, 14), dtype=np.float32)
    count = 0
    started = cpu()
    for index, family in enumerate(families):
        parameters = random.uniform(0, 1, generator.PARAMETER_COUNT)
        clean[index] = generator.clean_observations(parameters, int(family))
        targets[index] = generator.target_mass(parameters, int(family))
        count += 1
        if count % 2000 == 0:
            print("simulate", count, "cpu", round(cpu() - started, 2), flush=True)
        if cpu() - started >= 300 and count >= 8000:
            break
    clean, targets, families = clean[:count], targets[:count], families[:count]
    np.savez(ROOT / "simulations.npz", clean=clean, spectral_mass=targets, family=families)
    return clean, targets, families


def prepare(clean, targets, families, bands):
    selected = (families == 3) == (bands == 3)
    values, masses = clean[selected].astype(np.float64), targets[selected, :bands].copy()
    reference = .0012 * (1 + .35 * np.arange(2))[None, :, None] * (.6 + .4 / (1 + generator.OMEGA / 6))
    reference = np.broadcast_to(reference, (2, 2, len(generator.OMEGA))).copy()
    whitened = generator.whiten(values, reference).reshape(len(values), -1)
    center = whitened.mean(axis=0)
    covariance = (whitened - center).T @ (whitened - center) / len(values)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    basis = eigenvectors[:, -20:][:, ::-1].T.copy()
    scale = np.sqrt(np.maximum(eigenvalues[-20:][::-1], 0) + 1.3525)
    projection = dict(center=center, basis=basis, scale=scale, reference_sigma=reference)
    np.savez(ROOT / f"projection_{bands}.npz", **projection)
    compressed = ((whitened - center) @ basis.T / scale).astype(np.float32)
    random = np.random.default_rng(43281 + bands)
    order = random.permutation(len(values))
    validation_count = min(2000, max(512, len(values) // 10))
    heldout, training = order[:validation_count], order[validation_count:]
    relative_noise = np.exp(random.uniform(np.log(.5), np.log(2), len(heldout))).astype(np.float32)
    synthetic_features = np.column_stack((compressed[heldout] + random.normal(size=(len(heldout), 20)) * relative_noise[:, None] / scale,
                                          np.log(relative_noise) / np.log(2))).astype(np.float32)
    return dict(clean=torch.from_numpy(compressed[training]), targets=torch.from_numpy(masses[training]),
                scale=torch.from_numpy(scale.astype(np.float32)),
                synthetic_features=torch.from_numpy(synthetic_features), synthetic_targets=torch.from_numpy(masses[heldout]),
                eigenvalues=eigenvalues[-20:][::-1].tolist(), examples=len(training))


def train_model(data, bands, seed_index, allotted_cpu):
    torch.manual_seed(200391 + 17 * bands + seed_index)
    model = torch.nn.Sequential(torch.nn.Linear(21, 192), torch.nn.SiLU(),
                                torch.nn.Linear(192, 192), torch.nn.SiLU(),
                                torch.nn.Linear(192, 128), torch.nn.SiLU(),
                                torch.nn.Linear(128, bands * 14))
    with torch.no_grad():
        model[-1].weight.zero_()
        model[-1].bias.copy_(torch.log(data["targets"].mean(dim=0).clamp_min(1.e-6)).flatten())
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=1.e-5)
    scales = torch.tensor(generator.MASS_SCALES, dtype=torch.float32)
    started = cpu()
    best, best_state, step = np.inf, None, 0
    while cpu() - started < allotted_cpu and cpu() < 920:
        selected = torch.randint(0, len(data["clean"]), (512,))
        relative_noise = torch.exp(torch.empty(512).uniform_(np.log(.5), np.log(2)))
        noisy = data["clean"][selected] + torch.randn(512, 20) * relative_noise[:, None] / data["scale"]
        features = torch.cat((noisy, (torch.log(relative_noise) / np.log(2))[:, None]), dim=1)
        fraction = min((cpu() - started) / max(allotted_cpu, 1), 1)
        learning_rate = .0015 * (.08 + .92 * .5 * (1 + np.cos(np.pi * fraction)))
        optimizer.param_groups[0]["lr"] = learning_rate
        prediction = model(features).reshape(-1, bands, 14).softmax(dim=-1)
        squared = ((prediction - data["targets"][selected]) / scales) ** 2
        loss = torch.sqrt(squared.mean(dim=(1, 2)) + .02).mean() if seed_index == 2 else squared.mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.)
        optimizer.step()
        step += 1
        if step % 200 == 0:
            with torch.no_grad():
                validation = model(data["synthetic_features"]).reshape(-1, bands, 14).softmax(dim=-1)
                error = torch.sqrt((((validation - data["synthetic_targets"]) / scales) ** 2).mean(dim=(1, 2))).mean().item()
            if error < best:
                best = error
                best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            print("fit", bands, seed_index, step, "synthetic", round(error, 5), "cpu", round(cpu(), 2), flush=True)
    if best_state is not None:
        model.load_state_dict(best_state)
    linear = [layer for layer in model if isinstance(layer, torch.nn.Linear)]
    exported = {"layers": np.array(len(linear))}
    for index, layer in enumerate(linear):
        exported[f"weight_{index}"] = layer.weight.detach().numpy().copy()
        exported[f"bias_{index}"] = layer.bias.detach().numpy().copy()
    name = f"network_{bands}_{seed_index}.npz"
    np.savez_compressed(ROOT / name, **exported)
    with torch.no_grad():
        sample = data["synthetic_features"][:20]
        expected = model(sample).reshape(-1, bands, 14).softmax(dim=-1).numpy()
    actual = network_prediction(sample.numpy(), exported, bands)
    assert np.max(np.abs(actual - expected)) < 2.e-6
    return dict(file=name, bands=bands, seed_index=seed_index, steps=step,
                synthetic_core=best, cpu_seconds=cpu() - started)


def main():
    initial_cpu = cpu()
    clean, targets, families = simulate()
    prepared = {bands: prepare(clean, targets, families, bands) for bands in (2, 3)}
    with np.load(PUBLIC / "validation_features.npz", allow_pickle=False) as archive:
        validation = {key: archive[key] for key in archive.files}
    with np.load(PUBLIC / "validation_labels.npz", allow_pickle=False) as archive:
        labels, validation_families = archive["spectral_mass"], archive["family"]
    records = []
    for seed_index in range(3):
        for bands in (2, 3):
            models_remaining = 6 - len(records)
            allotted = min(100., max(12., (900 - cpu()) / models_remaining))
            record = train_model(prepared[bands], bands, seed_index, allotted)
            records.append(record)
            (ROOT / "training_progress.json").write_text(json.dumps(dict(cpu_seconds=cpu(), models=records), indent=2) + "\n")
    variants = ((0,), (1,), (2,), (0, 1), (0, 1, 2))
    evaluations = []
    for seeds in variants:
        selection = {"models": {str(bands): [f"network_{bands}_{seed}.npz" for seed in seeds] for bands in (2, 3)}}
        prediction = predict(validation["observed"], validation["sigma"], validation["sheet_count"], selection)
        result = metrics(prediction, labels, validation_families)
        evaluations.append(dict(selection=selection, validation=result))
        print("PUBLIC", seeds, json.dumps(result), flush=True)
    selected = min(evaluations, key=lambda record: record["validation"]["objective"])
    (ROOT / "selection.json").write_text(json.dumps(selected["selection"], indent=2) + "\n")
    prediction = predict(validation["observed"], validation["sigma"], validation["sheet_count"])
    np.savez_compressed(ROOT / "validation_prediction.npz", spectral_mass=prediction)
    report = dict(cpu_seconds=cpu(), initial_cpu_seconds=initial_cpu, synthetic_examples=len(clean),
                  training_counts={str(bands): prepared[bands]["examples"] for bands in (2, 3)},
                  simulation_seed=51829473, latent_parameters_saved=False,
                  training_data="Independent new simulations only; no hidden labels, hidden latents, or teacher initialization",
                  augmentation="Exact AR-whitened Gaussian noise projected onto an orthonormal signal basis, plus known log noise amplitude",
                  selection_data="public validation only; five predetermined ensemble variants",
                  models=records, validation_variants=evaluations, selected=selected,
                  budget="1000 CPU second hard training limit; remaining budget reserved for one frozen evaluation")
    (ROOT / "training_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("DONE", json.dumps(dict(cpu_seconds=cpu(), selected=selected)), flush=True)


if __name__ == "__main__":
    main()
