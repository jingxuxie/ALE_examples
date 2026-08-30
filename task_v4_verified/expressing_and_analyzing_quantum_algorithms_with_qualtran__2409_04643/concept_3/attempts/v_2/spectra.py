from analyze import SUITE, np

def walsh(values):
    values = values.copy()
    for bit in range(len(values).bit_length() - 1):
        view = values.reshape(-1, 2, 1 << bit)
        left = view[:, 0, :].copy()
        right = view[:, 1, :].copy()
        view[:, 0, :] = left + right
        view[:, 1, :] = left - right
    return values

if __name__ == '__main__':
    for inst in SUITE:
        table = np.array(inst['table'])
        print(inst['id'])
        for bit in range(inst['m']):
            spectrum = walsh(1 - 2 * ((table >> bit) & 1))
            best = np.argsort(-abs(spectrum))[:12]
            print(bit, [(int(mask), int(spectrum[mask])) for mask in best])
