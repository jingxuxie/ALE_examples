import numpy as np


def siam(n, tp, t, vg, u, v=0.0):
    assert n % 2 == 0
    idximp = n // 2 - 1
    idxls = np.arange(0, idximp, dtype=int)
    idxrs = np.arange(idximp + 1, n, dtype=int)
    h1e = np.zeros((n, n))
    g2e = np.zeros((n, n, n, n))
    g2e[idximp, idximp, idximp, idximp] = u / 2
    h1e[idximp, idximp] = vg
    h1e[idximp, idxls[-1]] = h1e[idxls[-1], idximp] = -tp
    h1e[idximp, idxrs[0]] = h1e[idxrs[0], idximp] = -tp
    for il, ilp in zip(idxls, idxls[1:]):
        h1e[ilp, il] = h1e[il, ilp] = -t
    for ir, irp in zip(idxrs, idxrs[1:]):
        h1e[irp, ir] = h1e[ir, irp] = -t
    for il in idxls:
        h1e[il, il] = -v / 2
    for ir in idxrs:
        h1e[ir, ir] = v / 2
    return h1e, g2e, idximp
