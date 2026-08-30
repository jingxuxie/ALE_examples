import numpy as np
from scipy.linalg import qr


def charge_bases(factors, random, count=24):
    vectors = []
    strengths = []
    for factor in factors:
        values, directions = np.linalg.eigh(factor)
        indices = np.argsort(-abs(values))
        vectors.append(directions[:, indices[0]])
        strengths.append(abs(values[indices[0]]))
        if abs(values[indices[1]]) > .12 * abs(values[indices[0]]):
            vectors.append(directions[:, indices[1]])
            strengths.append(abs(values[indices[1]]))
    vectors = np.array(vectors).T
    strengths = np.maximum(np.array(strengths), np.finfo(float).tiny)
    for index in range(count):
        if index == 0:
            order = np.argsort(-strengths)
            yield np.linalg.qr(vectors[:, order], mode='complete')[0]
        elif index == 1:
            order = np.argsort(strengths)
            yield np.linalg.qr(vectors[:, order], mode='complete')[0]
        else:
            temperature = [.35, .7, 1.4][index % 3]
            scores = np.log(strengths) + temperature * random.gumbel(size=len(strengths))
            if index % 2:
                order = np.argsort(-scores)
                yield np.linalg.qr(vectors[:, order], mode='complete')[0]
            else:
                weighted = vectors * np.exp(scores - max(scores))
                yield qr(weighted, mode='full', pivoting=True)[0]
