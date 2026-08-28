import numpy as np


def process_channel(case, options, propagator):
    dimension = len(case['H0'])
    channel = np.empty((dimension ** 2, dimension ** 2), dtype=complex)
    for column in range(dimension ** 2):
        operator = np.zeros((dimension, dimension), dtype=complex)
        operator[column // dimension, column % dimension] = 1
        final = propagator(case, operator, options)[-1]
        channel[:, column] = final.ravel()
    choi = channel.reshape(dimension, dimension, dimension, dimension).transpose(0, 2, 1, 3).reshape(dimension ** 2, dimension ** 2)
    return channel, choi
