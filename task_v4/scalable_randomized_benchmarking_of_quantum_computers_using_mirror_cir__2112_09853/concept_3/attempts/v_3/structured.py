import random
import subprocess
import re
from pathlib import Path

WORDS = ['I', 'H', 'S', 'HS', 'SH', 'HSH']


def action(word, value):
    xbit, zbit = value & 1, value >> 1
    for letter in word:
        if letter == 'H':
            xbit, zbit = zbit, xbit
        if letter == 'S':
            zbit ^= xbit
    return xbit | zbit << 1


def combine(words):
    joined = ''.join(words)
    return next(index for index, word in enumerate(WORDS)
                if all(action(joined, value) == action(word, value) for value in (1, 2)))


rng = random.Random(29812)
best = None
for trial in range(12):
    horizontal_even = [(row + site, row + site + 1) for row in (0, 8) for site in (0, 2, 4, 6)]
    horizontal_odd = [(row + site, row + site + 1) for row in (0, 8) for site in (1, 3, 5)]
    removed = [(1, 2), (3, 4), (5, 6), (2, 5)]
    layers = []
    previous_targets = set()
    for round_index in range(12):
        color = (round_index + trial // 4) % 3
        gates = horizontal_even if color == 0 else horizontal_odd if color == 1 else [(site, site + 8) for site in range(8) if site not in removed[round_index // 3]]
        current_targets = {target for control, target in gates}
        kick = ['SH', 'HS', 'H', 'HSH'][trial % 4]
        local = [combine(['H' if site in previous_targets else '', kick, 'H' if site in current_targets else '']) for site in range(16)]
        layers.append((local, gates))
        previous_targets = current_targets
    prefix = f'struct_{trial}'
    text = '16 12\n' + '\n'.join(' '.join(map(str, local + [len(gates)] + [site for gate in gates for site in gate])) for local, gates in layers) + '\n'
    Path(prefix + '.seed').write_text(text)
    subprocess.run(['./search24', 'ladder16', str(31000 + trial), '3', prefix, prefix + '.seed', 'ideal', '3', 'fixed'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    checked = subprocess.run(['./search24', 'ladder16', '1', '0', 'unused', prefix + '.best', 'mitmtest'], capture_output=True, text=True)
    cost = int(re.search(r'fast=(\d+)', checked.stderr).group(1))
    print(trial, cost, flush=True)
    if best is None or cost < best[0]:
        best = (cost, prefix + '.best')
        Path('structured_best.path').write_text(best[1])
print('BEST', best, flush=True)
subprocess.run(['./search24', 'ladder16', '32001', '600', 'ladder_struct_sa', best[1], 'record', '2', 'global', '1', '5'])
