import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent / 'submission'))
sys.path.insert(0, '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/scalable_randomized_benchmarking_of_quantum_computers_using_mirror_cir__2112_09853/concept_2/participant/workspace')
from policy import Policy
if '--exact' in sys.argv:
    from variants import ExactPolicy as Policy
    sys.argv.remove('--exact')
if '--focused' in sys.argv:
    from variants import FocusedPolicy as Policy
    sys.argv.remove('--focused')
if '--improved' in sys.argv:
    from variants import ImprovedPolicy as Policy
    sys.argv.remove('--improved')
if '--debiased' in sys.argv:
    from debiased import DebiasedPolicy as Policy
    sys.argv.remove('--debiased')
if '--entropy' in sys.argv:
    from entropy import EntropyPolicy as Policy
    sys.argv.remove('--entropy')
if '--dense' in sys.argv:
    from dense import DensePolicy as Policy
    sys.argv.remove('--dense')
if '--subsets' in sys.argv:
    from subsets import SubsetPolicy as Policy
    sys.argv.remove('--subsets')
if '--sequential' in sys.argv:
    from subsets import SequentialPolicy as Policy
    sys.argv.remove('--sequential')
if '--balanced' in sys.argv:
    from balanced import BalancedPolicy as Policy
    sys.argv.remove('--balanced')
if '--short' in sys.argv:
    from balanced import ShortPolicy as Policy
    sys.argv.remove('--short')
if '--beam' in sys.argv:
    from beam import BeamPolicy as Policy
    sys.argv.remove('--beam')
if '--tempered' in sys.argv:
    from tempered import TemperedPolicy as Policy
    sys.argv.remove('--tempered')
if '--support' in sys.argv:
    from support import SupportPolicy as Policy
    sys.argv.remove('--support')
if '--allocation' in sys.argv:
    from allocation import AllocationPolicy as Policy
    sys.argv.remove('--allocation')
if '--candidate' in sys.argv:
    from tempered import FinalCandidatePolicy as Policy
    sys.argv.remove('--candidate')
if '--hybrid' in sys.argv:
    from hybrid import HybridPolicy as Policy
    sys.argv.remove('--hybrid')
from model import Episode, FAMILIES, SHAPES
import numpy as np


class RecordedPolicy(Policy):
    def posterior(self, *args, **kwargs):
        self.last_posterior = super().posterior(*args, **kwargs)
        return self.last_posterior

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=5000)
parser.add_argument('--shape', type=int, default=-1)
parser.add_argument('--family', type=int, default=-1)
parser.add_argument('--log', default='research.jsonl')
parser.add_argument('--fixtures', default='')
arguments = parser.parse_args()
with open(arguments.log, 'w') as output:
    for family_index, family in enumerate(FAMILIES):
        if arguments.family >= 0 and arguments.family != family_index:
            continue
        for shape_index, shape in enumerate(SHAPES):
            if arguments.shape >= 0 and arguments.shape != shape_index:
                continue
            seed = arguments.seed+1009*family_index+53*shape_index
            episode = Episode(seed, family, shape)
            started = time.time()
            policy = RecordedPolicy(episode.hello())
            policy.run(episode.handle)
            record = dict(family=family, shape=shape, seed=seed, seconds=time.time()-started, **episode.metrics())
            unused, features = policy.grid.features(episode.targets)
            posterior_rates = -np.expm1(-(policy.last_posterior[:, :policy.rate_dimension] @ features.T))
            posterior_risk = np.mean(((posterior_rates-np.asarray(episode.predictions))/(0.003+0.1*posterior_rates))**2)
            record.update(posterior_risk=float(posterior_risk), sizes=[len(observation['matching']) for observation in policy.observations],
                          depths=[observation['depth'] for observation in policy.observations])
            record['prediction_mean'] = float(np.mean(episode.predictions))
            if arguments.fixtures:
                destination = Path(arguments.fixtures)
                destination.mkdir(exist_ok=True)
                fixture = dict(hello=episode.hello(), observations=policy.observations, targets=episode.targets,
                               truths=[episode.error_rate(matching) for matching in episode.targets], predictions=episode.predictions,
                               base=episode.base.tolist(), crosstalk=episode.crosstalk.tolist())
                (destination / (family+'_'+str(seed)+'.json')).write_text(json.dumps(fixture))
            print(json.dumps(record), flush=True)
            output.write(json.dumps(record)+'\n')
            output.flush()
