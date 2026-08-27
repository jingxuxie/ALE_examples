import numpy as np
from scipy.ndimage import minimum_filter


def detect(psi, model):
    density = np.abs(psi) ** 2
    minima = density == minimum_filter(density, size=5)
    rows, columns = np.where(minima & (density < 0.15 * density.max()) & (model.roi > 0))
    return np.column_stack([model.x[columns], model.y[rows], np.ones(len(rows))])
