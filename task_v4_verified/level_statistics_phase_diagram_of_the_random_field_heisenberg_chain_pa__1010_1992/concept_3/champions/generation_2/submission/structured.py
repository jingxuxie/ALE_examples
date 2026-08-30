import search
import numpy as np

def structured(random, count):
    candidates = []
    while len(candidates) < count:
        mode = int(random.integers(9))
        amplitude = random.uniform(1.5, 7.5)
        disorder = np.exp(random.uniform(np.log(.12), np.log(1.0)))
        fields = random.uniform(-disorder, disorder, 12)
        if mode == 0:
            split = int(random.integers(2, 11))
            fields[:split] += amplitude
            fields[split:] -= amplitude
        elif mode == 1:
            positions = random.choice(12, int(random.integers(1, 4)), replace=False)
            fields[positions] += amplitude * random.choice([-1., 1.], len(positions))
        elif mode == 2:
            fields += np.tile(random.uniform(-amplitude, amplitude, int(random.choice([2, 3, 4, 6]))), 12)[:12]
        elif mode == 3:
            split = int(random.integers(3, 10))
            fields[:split] += np.linspace(-amplitude, amplitude, split)
            fields[split:] += random.uniform(-amplitude, amplitude)
        elif mode == 4:
            blocks = int(random.choice([2, 3, 4, 6]))
            fields += np.repeat(random.uniform(-amplitude, amplitude, blocks), 12 // blocks)
        elif mode == 5:
            fields += amplitude * np.cos(2 * np.pi * np.arange(12) / 12 + random.uniform(0, 2 * np.pi))
        elif mode == 6:
            pattern = random.uniform(-amplitude, amplitude, 6)
            fields += np.concatenate([pattern, -pattern])
        elif mode == 7:
            fields += amplitude * (np.arange(12) / 11) ** random.uniform(.3, 4)
        else:
            fields += random.choice([-amplitude, 0., amplitude], 12)
        fields -= fields.mean()
        try:
            search.validate_fields(fields)
        except ValueError:
            continue
        candidates.append(fields.tolist())
    return candidates

search.generate = structured
search.main()
