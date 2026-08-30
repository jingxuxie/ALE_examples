from reduced import *
import subprocess
from enumerate_blocks import compositions

values = []
for point in MODEL['certification_points']:
    beta = MODEL['beta'] * point['beta_multiplier']
    chemical = MODEL['chemical_potential'] + point['chemical_shift']
    coupling = np.arccosh(np.exp(beta / 8))
    kinetic = expm(-beta / 16 * REDUCED_KINETIC)
    values.extend([coupling, np.exp(beta * chemical)])
    for length in range(1, 17):
        for state in range(16):
            field = np.array([1 if state & (1 << site) else -1 for site in range(4)])
            for spin in [1, -1]:
                factor = kinetic * np.exp(spin * coupling * field)[None]
                values.extend(np.linalg.matrix_power(factor, length).reshape(-1))
for rotation in range(4):
    for reflection in range(2):
        mapping = []
        for site in range(4):
            horizontal, vertical = divmod(site, 2)
            if reflection:
                horizontal = 1 - horizontal
            for step in range(rotation):
                horizontal, vertical = vertical, 1 - horizontal
            mapping.append(2 * horizontal + vertical)
        for inversion in [0, 15]:
            values.extend([sum(((state >> site) & 1) << mapping[site] for site in range(4)) ^ inversion for state in range(16)])
for count in [6, 7, 8]:
    schedules = []
    for lengths in compositions(16, count):
        orientations = [lengths[offset:] + lengths[:offset] for offset in range(count)]
        backwards = lengths[::-1]
        orientations += [backwards[offset:] + backwards[:offset] for offset in range(count)]
        if lengths != min(orientations):
            continue
        if count == 7 and (max(lengths) > 4 or lengths.count(1) < 3):
            continue
        if count == 8 and sorted(lengths) != [1, 1, 1, 1, 3, 3, 3, 3]:
            continue
        schedules.append(lengths)
    schedules.sort(key=lambda lengths: (max(lengths) > 4, abs(lengths.count(1) - (count - 4)), sum(length * length for length in lengths)))
    print('Schedules', count, len(schedules), flush=True)
    for lengths in schedules:
        values.extend([count] + list(lengths))
payload = ' '.join(str(value) for value in values)
result = subprocess.run([str(ROOT / 'exhaustive8')], input=payload, text=True, stdout=subprocess.PIPE)
print(result.stdout, flush=True)
if result.stdout.startswith('FOUND'):
    integers = [int(value) for value in result.stdout.split()[1:]]
    count = integers[0]
    sequence, lengths = integers[1:count + 1], integers[count + 1:]
    reduced = np.repeat(np.array([[1 if state & (1 << site) else -1 for site in range(4)] for state in sequence], dtype=np.int8), lengths, axis=0)
    candidate = reduced[:, MAPPING]
    signs = [evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] for point in MODEL['certification_points']]
    print('Full signs', signs, flush=True)
    if all(sign < 0 for sign in signs):
        save(candidate, 'found_exhaustive8.json')
        save(candidate, 'witness.json')
