import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

from diagnostics import BOUND, PRODUCTS, STATES, evaluate, write_witness


def screen(filename, max_candidates=None):
    candidates = [json.loads(line) for line in Path(filename).read_text().splitlines()]
    best_score = 0
    best_variance = 1e9
    start = time.time()
    summaries = []
    for candidate_index, candidate in enumerate(candidates[:max_candidates]):
        anchor = 1 - 2 * ((candidate['anchor'] >> np.arange(16)) & 1)
        pattern = 1 - 2 * ((candidate['center'] >> np.arange(16)) & 1)
        free = [site for site in range(16) if (candidate['free'] >> site) & 1]
        fixed = [site for site in range(16) if site not in free]
        energy = -PRODUCTS @ np.asarray(candidate['bonds'])
        relative = STATES * anchor
        center_distance = (16 - STATES @ pattern) / 2
        sector = np.minimum(center_distance, 16 - center_distance) <= candidate['radius']
        for root in fixed:
            fixed_errors = (len(fixed) - (relative[:, fixed] * relative[:, root, None]).sum(axis=1)) / 2
            logq = -(len(free) + 1) * np.log(2) - fixed_errors * BOUND - (len(fixed) - 1) * np.log1p(np.exp(-BOUND))
            proposal = np.exp(logq)
            mean_energy = proposal @ energy
            mean_logq = proposal @ logq
            centered_energy = energy - mean_energy
            centered_logq = logq - mean_logq
            energy_variance = proposal @ centered_energy ** 2
            covariance = proposal @ (centered_energy * centered_logq)
            beta = float(np.clip(-covariance / energy_variance, 1, 3))
            variance = proposal @ (beta * centered_energy + centered_logq) ** 2
            log_partition = logsumexp(-beta * energy)
            target = np.exp(-beta * energy - log_partition)
            mean_error = abs((proposal - target) @ (beta * energy)) / 16
            target_mass = target @ sector
            proposal_mass = proposal @ sector
            score = min(1, .05 / variance, .02 / max(mean_error, 1e-300), target_mass / .35,
                        .001 / max(proposal_mass, 1e-300), -mean_logq / 3,
                        (beta * mean_energy + mean_logq + log_partition) / .4)
            summaries.append({'candidate': candidate_index, 'root': root, 'beta': beta,
                              'variance': variance, 'score_without_gradient': score,
                              'target_mass': target_mass, 'proposal_mass': proposal_mass})
            if score > best_score or (score == best_score and variance < best_variance):
                order = [root] + [site for site in fixed if site != root] + free
                weights = np.zeros((16, 16))
                for position, site in enumerate(order[1:len(fixed)], 1):
                    weights[position, 0] = (BOUND - 1e-12) * anchor[site] * anchor[root]
                witness = write_witness('candidate.json', candidate['bonds'], beta, order, weights, pattern, candidate['radius'])
                metrics = evaluate(witness)
                actual_score = metrics['worst_score']
                if actual_score > best_score or (actual_score == best_score and variance < best_variance):
                    best_score = actual_score
                    best_variance = variance
                    Path('witness.json').write_text(json.dumps(witness, indent=2) + '\n')
                    Path('metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
                    print(candidate_index, root, 'beta', beta, 'score', best_score, 'variance', variance,
                          'gradient', metrics['gradient_infinity'], 'masses', target_mass, proposal_mass,
                          'elapsed', time.time() - start, flush=True)
    summaries.sort(key=lambda summary: (-summary['score_without_gradient'], summary['variance']))
    Path('screen_results.json').write_text(json.dumps(summaries, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('candidates', nargs='?', default='candidates.jsonl')
    parser.add_argument('--limit', type=int)
    arguments = parser.parse_args()
    screen(arguments.candidates, arguments.limit)
