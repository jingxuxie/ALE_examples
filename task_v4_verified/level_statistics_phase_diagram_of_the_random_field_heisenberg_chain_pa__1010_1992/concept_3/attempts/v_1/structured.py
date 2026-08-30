import search
from search import np, valid

def generate(random, count):
    candidates = []
    sites = np.arange(12)
    while len(candidates) < count:
        kind = int(random.integers(10))
        strength = random.uniform(0.65, 3.8)
        noise = np.exp(random.uniform(np.log(0.12), np.log(0.9)))
        if kind < 7:
            fields = (-1.) ** sites * strength
            if kind == 6:
                fields += random.uniform(-0.6, 0.6) * np.cos(2 * np.pi * sites / random.choice([3, 4, 6, 12]) + random.uniform(0, 2*np.pi))
        elif kind == 7:
            split = int(random.integers(3, 10))
            fields = strength * np.where(sites < split, 1., -1.)
        elif kind == 8:
            fields = strength * np.cos(2 * np.pi * sites / 12 + random.uniform(0, 2*np.pi))
        else:
            fields = strength * np.linspace(-1, 1, 12)
        fields += random.normal(0, noise, 12)
        fields -= fields.mean()
        if valid(fields):
            candidates.append((fields.tolist(), 20+kind))
    return candidates

if __name__ == '__main__':
    search.generate = generate
    search.main()
