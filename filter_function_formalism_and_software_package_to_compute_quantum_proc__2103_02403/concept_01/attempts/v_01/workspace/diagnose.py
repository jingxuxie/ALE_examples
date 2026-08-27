import argparse
import json
from pathlib import Path

import numpy as np

from pipeline.physics import ideal_channel, load_case


def ensemble_check(case, arrays, batches=16, batch_size=256, max_step=0.025, seed=1907):
    law = case['noise']
    if law['kind'] not in ('static', 'ou', 'telegraph'):
        raise ValueError('This diagnostic covers static, OU, and telegraph calibration only.')
    random = np.random.default_rng(seed)
    sigma = np.asarray(law['sigma'])
    mixing = np.asarray(law['mixing'])
    rates = np.asarray(law.get('rates', np.zeros_like(sigma)))
    dimension = arrays['H'].shape[-1]
    ideal = ideal_channel(arrays)
    infidelities = []
    coherences = []
    for batch in range(batches):
        latent = random.normal(size=(batch_size, len(sigma))) * sigma
        if law['kind'] == 'telegraph':
            latent = np.where(latent >= 0, sigma, -sigma)
        propagators = np.broadcast_to(np.eye(dimension), (batch_size, dimension, dimension)).astype(complex).copy()
        for duration, control, sensitivity in zip(arrays['dt'], arrays['H'], arrays['sensitivity']):
            subdivisions = 1 if law['kind'] == 'static' else max(1, int(np.ceil(duration / max_step)))
            step = duration / subdivisions
            for iteration in range(subdivisions):
                beta = latent @ mixing.T
                noise = np.einsum('ba,a,aij->bij', beta, sensitivity, arrays['operators'])
                eigenvalues, eigenvectors = np.linalg.eigh(control + noise)
                increments = (eigenvectors * np.exp(-1j * step * eigenvalues)[:, None, :]) @ eigenvectors.conj().transpose(0, 2, 1)
                propagators = increments @ propagators
                if law['kind'] == 'ou':
                    decay = np.exp(-rates * step)
                    latent = latent * decay + random.normal(size=latent.shape) * sigma * np.sqrt(1 - decay ** 2)
                elif law['kind'] == 'telegraph':
                    flips = random.random(latent.shape) < -np.expm1(-2 * rates * step) / 2
                    latent = np.where(flips, -latent, latent)
        channel = np.einsum('bik,bjl->ijkl', propagators.conj(), propagators).reshape(dimension ** 2, dimension ** 2) / batch_size
        error = ideal.conj().T @ channel
        infidelities.append(1 - np.trace(error).real / dimension ** 2)
        coherences.append(float((error[1, 0] - error[0, 1].conj()).imag / 2))
    return dict(case_id=case['case_id'], samples=batches * batch_size, seed=seed,
                max_step=max_step, infidelity=float(np.mean(infidelities)),
                infidelity_se=float(np.std(infidelities, ddof=1) / np.sqrt(batches)),
                coherent_probe=float(np.mean(coherences)),
                coherent_probe_se=float(np.std(coherences, ddof=1) / np.sqrt(batches)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case')
    parser.add_argument('destination')
    parser.add_argument('--batches', type=int, default=16)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--max-step', type=float, default=0.025)
    parser.add_argument('--seed', type=int, default=1907)
    arguments = parser.parse_args()
    case, arrays = load_case(arguments.case)
    result = ensemble_check(case, arrays, arguments.batches, arguments.batch_size, arguments.max_step, arguments.seed)
    Path(arguments.destination).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
