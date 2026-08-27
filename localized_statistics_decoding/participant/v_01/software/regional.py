import numpy as np

from binary import solve_binary


def hypothesis(case, shot, mode):
    faults = case['faults']
    regions = case['detector_regions']
    correction = np.zeros(len(faults), dtype=np.uint8)
    syndrome = [0 if value is None else value for value in shot['syndrome']]
    for region in sorted(set(regions)):
        rows = [index for index, owner in enumerate(regions) if owner == region]
        columns = [index for index, fault in enumerate(faults)
                   if fault['detectors'] and regions[fault['detectors'][0]] == region]
        matrix = np.asarray([[int(row in faults[column]['detectors']) for column in columns]
                             for row in rows], dtype=np.uint8)
        probabilities = np.asarray([faults[column]['probabilities'][mode] for column in columns])
        order = np.argsort(-probabilities)
        local = solve_binary(matrix, [syndrome[row] for row in rows], order)
        correction[columns] = local
    return correction
