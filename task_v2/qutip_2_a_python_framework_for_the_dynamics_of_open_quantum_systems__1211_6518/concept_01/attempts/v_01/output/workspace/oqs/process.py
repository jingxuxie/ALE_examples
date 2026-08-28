import numpy as np


def operator_basis(dimension):
    return np.eye(dimension ** 2, dtype=complex).reshape(dimension ** 2, dimension, dimension).transpose(0, 2, 1)


def channel_from_outputs(outputs):
    return outputs.transpose(0, 2, 1).reshape(len(outputs), len(outputs)).T


def channel_to_choi(channel):
    dimension = int(round(np.sqrt(len(channel))))
    return channel.reshape(dimension, dimension, dimension, dimension).transpose(3, 1, 2, 0).reshape(channel.shape)


def process_channel(case, options, propagator):
    outputs = propagator(case, operator_basis(len(case['H0'])), options)[-1]
    channel = channel_from_outputs(outputs)
    return channel, channel_to_choi(channel)
