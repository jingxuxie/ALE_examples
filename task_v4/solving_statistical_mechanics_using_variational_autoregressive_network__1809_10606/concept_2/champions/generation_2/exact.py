import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import json
from pathlib import Path
import numpy as np
from scipy.special import expit, logsumexp

BOUND = np.log(999.)
INDICES = np.arange(65536, dtype=np.int64)
SPINS = 2 * ((INDICES[:, None] >> np.arange(16)) & 1) - 1
SPINS = SPINS.astype(np.float64)
EDGES = np.array([(site, 4*(site//4)+(site+1)%4) if direction == 0 else
                  (site, (site+4)%16) for site in range(16) for direction in range(2)])
PRODUCTS = SPINS[:, EDGES[:, 0]] * SPINS[:, EDGES[:, 1]]
LOWER = np.tril_indices(16, -1)

def energies(bonds):
    return -(PRODUCTS @ np.asarray(bonds))

def frustrated(bonds):
    bonds = np.asarray(bonds)
    return sum(bonds[2*site] * bonds[2*(4*(site//4)+(site+1)%4)+1] *
               bonds[2*((site+4)%16)] * bonds[2*site+1] < 0 for site in range(16))

def fwht(values):
    values = np.array(values, dtype=float, copy=True)
    width = 1
    while width < len(values):
        blocks = values.reshape(-1, 2*width)
        first = blocks[:, :width].copy()
        blocks[:, :width] += blocks[:, width:]
        blocks[:, width:] = first - blocks[:, width:]
        width *= 2
    return values

POPCOUNT = ((SPINS+1)/2).sum(axis=1)
SECTOR_KERNELS = {radius: fwht(((POPCOUNT <= radius) | (POPCOUNT >= 16-radius)).astype(float))
                  for radius in (2, 3, 4)}

def sector_masses(probabilities, radius):
    return fwht(fwht(probabilities)*SECTOR_KERNELS[radius])/65536

def evaluate(witness, find_sector=False, details=False):
    spins = SPINS[:, witness['order']]
    weights = np.asarray(witness['weights'])
    logits = spins @ weights.T
    logq = -np.logaddexp(0, -spins*logits).sum(axis=1)
    proposal = np.exp(logq)
    potential = witness['beta']*energies(witness['bonds'])
    logz = logsumexp(-potential)
    target = np.exp(-potential-logz)
    reward = potential+logq
    average = proposal @ reward
    centered = reward-average
    gradient = (((spins+1)/2-expit(logits))*(proposal*centered)[:, None]).T @ spins
    distance = ((16-SPINS @ np.asarray(witness['pattern']))/2).astype(int)
    sector = (distance <= witness['radius']) | (distance >= 16-witness['radius'])
    metrics = dict(entropy=float(-proposal @ logq), reverse_kl=float(average+logz),
                   reward_variance=float(proposal @ centered**2),
                   gradient_infinity=float(np.abs(gradient[LOWER]).max()),
                   energy_error_per_spin=float(abs((proposal-target) @ potential)/16),
                   target_sector_mass=float(target[sector].sum()),
                   proposal_sector_mass=float(proposal[sector].sum()))
    scores = [metrics['entropy']/3, metrics['reverse_kl']/.4,
              .05/max(metrics['reward_variance'], 1e-300),
              .003/max(metrics['gradient_infinity'], 1e-300),
              .02/max(metrics['energy_error_per_spin'], 1e-300),
              metrics['target_sector_mass']/.35, .001/max(metrics['proposal_sector_mass'], 1e-300)]
    metrics.update(score=float(min(1, *scores)), normalization=float(proposal.sum()),
                   symmetry=float(abs(proposal-proposal[::-1]).max()),
                   row_l1_max=float(np.abs(weights).sum(axis=1).max()),
                   frustrated=int(frustrated(witness['bonds'])),
                   mean_energy_q=float(proposal @ potential), mean_energy_p=float(target @ potential))
    if find_sector:
        options = []
        for radius in (2, 3, 4):
            pmass = sector_masses(target, radius)
            qmass = sector_masses(proposal, radius)
            quality = np.minimum(pmass/.35, .001/np.maximum(qmass, 1e-300))
            center = np.argmax(quality)
            options.append((float(quality[center]), int(radius), int(center), float(pmass[center]), float(qmass[center])))
        metrics['best_sectors'] = sorted(options, reverse=True)
    if details:
        return metrics, proposal, target, gradient
    return metrics

def save(witness, path='witness.json'):
    Path(path).write_text(json.dumps(witness, indent=2, allow_nan=False)+'\n')

if __name__ == '__main__':
    import sys
    witness = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(evaluate(witness, find_sector=True), indent=2))
