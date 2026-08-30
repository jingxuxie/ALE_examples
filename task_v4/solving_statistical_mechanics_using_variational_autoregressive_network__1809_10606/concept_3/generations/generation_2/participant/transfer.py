"""Exact finite, open-strip Ising inference; no material parameters are included."""

import numpy as np


def spin_states(height):
    if not 1 <= height <= 12:
        raise ValueError("height must be between 1 and 12")
    return (2 * ((np.arange(1 << height)[:, None] >> np.arange(height)) & 1) - 1).astype(np.int8)


def lattice_edges(height, columns):
    vertical = [(column * height + row, column * height + row + 1)
                for column in range(columns) for row in range(height - 1)]
    horizontal = [(column * height + row, (column + 1) * height + row)
                  for column in range(columns - 1) for row in range(height)]
    return np.asarray(vertical + horizontal, dtype=np.int64)


class StripIsing:
    """Arrays: vertical[C,H-1], horizontal[C-1,H], fields[C,H]."""

    def __init__(self, vertical, horizontal, fields):
        self.fields = np.asarray(fields, dtype=np.float64)
        if self.fields.ndim != 2:
            raise ValueError("fields must have shape (columns, height)")
        self.columns, self.height = self.fields.shape
        self.vertical = np.asarray(vertical, dtype=np.float64)
        self.horizontal = np.asarray(horizontal, dtype=np.float64)
        if self.vertical.shape != (self.columns, self.height - 1):
            raise ValueError("invalid vertical shape")
        if self.horizontal.shape != (self.columns - 1, self.height):
            raise ValueError("invalid horizontal shape")
        if self.columns < 1 or not all(np.isfinite(values).all() for values in
                                       (self.vertical, self.horizontal, self.fields)):
            raise ValueError("invalid parameters")
        self.states = spin_states(self.height)
        self.vertical_products = self.states[:, :-1] * self.states[:, 1:]

    def _transfer(self, weights, couplings, beta):
        result = weights.copy()
        for row, coupling in enumerate(couplings):
            stride = 1 << row
            blocks = result.reshape(-1, 2, stride)
            same = np.exp(beta * coupling - abs(beta * coupling))
            different = np.exp(-beta * coupling - abs(beta * coupling))
            negative = blocks[:, 0, :].copy()
            positive = blocks[:, 1, :].copy()
            blocks[:, 0, :] = same * negative + different * positive
            blocks[:, 1, :] = different * negative + same * positive
        return result

    def _messages(self, beta, field_delta=None, evidence=None):
        if not np.isfinite(beta) or beta <= 0:
            raise ValueError("beta must be positive and finite")
        delta = np.zeros_like(self.fields) if field_delta is None else np.asarray(field_delta, dtype=np.float64)
        if delta.shape != self.fields.shape or not np.isfinite(delta).all():
            raise ValueError("invalid field_delta")
        log_unary = beta * (self.vertical @ self.vertical_products.T +
                            (self.fields + delta) @ self.states.T)
        if evidence is not None:
            observed = np.asarray(evidence)
            if observed.shape != self.fields.shape or not np.isin(observed, (-1, 0, 1)).all():
                raise ValueError("evidence must have shape (columns,height) and entries -1,0,1")
            for column in range(self.columns):
                compatible = np.all((observed[column] == 0) | (observed[column] == self.states), axis=1)
                log_unary[column, ~compatible] = -np.inf
        shifts = np.max(log_unary, axis=1)
        unary = np.exp(log_unary - shifts[:, None])
        forward = np.empty_like(unary)
        norm = unary[0].sum()
        forward[0] = unary[0] / norm
        log_partition = shifts[0] + np.log(norm)
        for column in range(1, self.columns):
            propagated = self._transfer(forward[column - 1], self.horizontal[column - 1], beta)
            weights = unary[column] * propagated
            norm = weights.sum()
            if norm <= 0 or not np.isfinite(norm):
                raise FloatingPointError("normalization failed")
            forward[column] = weights / norm
            log_partition += shifts[column] + np.log(norm) + np.abs(beta * self.horizontal[column - 1]).sum()
        backward = np.ones_like(unary)
        for column in range(self.columns - 2, -1, -1):
            weights = self._transfer(unary[column + 1] * backward[column + 1],
                                     self.horizontal[column], beta)
            backward[column] = weights / weights.max()
        marginals = forward * backward
        marginals /= marginals.sum(axis=1, keepdims=True)
        return float(log_partition), forward, marginals

    def log_partition(self, beta, field_delta=None, evidence=None):
        return self._messages(beta, field_delta, evidence)[0]

    def column_marginals(self, beta, field_delta=None, evidence=None):
        return self._messages(beta, field_delta, evidence)[2]

    def joint(self, beta, readout, field_delta=None):
        readout = np.asarray(readout, dtype=np.int64)
        if readout.ndim != 1 or len(readout) == 0 or len(set(readout.tolist())) != len(readout):
            raise ValueError("readout must contain distinct spin indices")
        if np.any(readout < 0) or np.any(readout >= self.columns * self.height):
            raise ValueError("readout outside lattice")
        columns = readout // self.height
        if not np.all(columns == columns[0]):
            raise ValueError("joint supports readouts in one column")
        marginal = self.column_marginals(beta, field_delta)[columns[0]]
        codes = ((self.states[:, readout % self.height] + 1) // 2) @ (1 << np.arange(len(readout)))
        result = np.bincount(codes, weights=marginal, minlength=1 << len(readout))
        return result / result.sum()

    def sample(self, beta, count, rng=None, field_delta=None):
        if not isinstance(count, (int, np.integer)) or count < 1:
            raise ValueError("count must be a positive integer")
        rng = np.random.default_rng() if rng is None else rng
        _, forward, _ = self._messages(beta, field_delta)
        indices = np.empty((count, self.columns), dtype=np.int64)
        indices[:, -1] = rng.choice(len(self.states), size=count, p=forward[-1])
        for column in range(self.columns - 2, -1, -1):
            interaction = beta * (self.states * self.horizontal[column]) @ self.states.T
            logits = np.log(forward[column])[None, :] + interaction.T
            logits -= logits.max(axis=1, keepdims=True)
            conditional = np.exp(logits)
            conditional /= conditional.sum(axis=1, keepdims=True)
            cumulative = np.cumsum(conditional, axis=1)
            cumulative[:, -1] = 1.0
            uniforms = rng.random(count)
            indices[:, column] = np.sum(cumulative[indices[:, column + 1]] < uniforms[:, None], axis=1)
        return self.states[indices].reshape(count, self.columns * self.height)


def model_from_edges(spec, couplings, fields):
    height, columns = spec["height"], spec["columns"]
    couplings = np.asarray(couplings, dtype=np.float64)
    if couplings.shape != (len(spec["edges"]),):
        raise ValueError("invalid coupling vector")
    split = columns * (height - 1)
    return StripIsing(couplings[:split].reshape(columns, height - 1),
                      couplings[split:].reshape(columns - 1, height),
                      np.asarray(fields).reshape(columns, height))
