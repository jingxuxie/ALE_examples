import json
from pathlib import Path

experiments = [
    ('branch1', 677832, 32, 18, 'iid_32', False),
    ('branch2', 297532, 32, 18, 'iid_32', False),
    ('branch3', 891623, 32, 18, 'iid_32', False),
    ('branch4', 443902, 32, 18, 'iid_32', False),
    ('branch5', 1729364, 64, 34, 'iid_32', False),
    ('branch6', 6248591, 64, 34, 'iid_32', False),
    ('branch7', 7482911, 32, 16, 'iid_32', False),
    ('branch8', 81576392, 128, 64, 'iid_32', False),
    ('branch9', 83764921, 64, 32, 'iid_32', False),
    ('branch10', 91367425, 128, 64, 'iid_32', False),
    ('branch11', 63519378, 64, 26, 'iid_32', True),
    ('branch_core', 4897136, 48, 24, 'density_mixture', False),
    ('branch_core2', 19377429, 64, 28, 'density_mixture', True),
    ('branch_core3', 28963742, 64, 28, 'density_mixture', True),
    ('branch_core4', 77631294, 128, 56, 'density_mixture', True),
    ('branch_core5', 45981736, 256, 112, 'density_mixture', True),
    ('branch_public', 942617, 96, 42, 'density_mixture', True),
]
results = []
for name, seed, count, minimum, distribution, symmetry in experiments:
    path = Path(name + '.log')
    if not path.exists():
        continue
    rows = [line.split() for line in path.read_text().splitlines()]
    depths = {int(row[1]): int(row[2]) for row in rows if row and row[0] == 'DEPTH'}
    candidates = {row[2]: float(row[1]) for row in rows if row and row[0] == 'POOL'}
    order = 3 if symmetry else 1 if name == 'branch2' else 0
    lookahead = symmetry or name in ['branch9', 'branch10']
    command = ['./optimize', 'branch', str(seed), str(count), str(minimum),
               str(order), '', 'mix' if distribution == 'density_mixture' else 'plain',
               'look' if lookahead else 'plain', 'sym' if symmetry else 'plain']
    if name == 'branch_public':
        command.append('public_search.txt')
    results.append({
        'log': str(path), 'seed': seed, 'scale': 1, 'screening_count': count,
        'support_generator': 'published_python' if name == 'branch_public' else 'mt19937_64',
        'command': command,
        'minimum_screening_successes': minimum, 'distribution': distribution,
        'uses_verified_spatial_symmetries': symmetry, 'complete': 24 in depths,
        'assignments_in_search_space': 3 ** 24,
        'visited_nodes': sum(depths.values()) if depths else None,
        'retained_leaves': depths.get(24),
        'independent_validation_fractions': candidates,
    })
Path('search_summary.json').write_text(json.dumps(results, indent=2) + '\n')
for result in results:
    print(result['log'], 'complete' if result['complete'] else 'incomplete',
          result['retained_leaves'],
          max(result['independent_validation_fractions'].values(), default=None))
