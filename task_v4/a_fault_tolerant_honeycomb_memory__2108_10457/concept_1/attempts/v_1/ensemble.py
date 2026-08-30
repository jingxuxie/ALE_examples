import time

import numpy as np
import pymatching
import stim


def ensemble(model, syndromes, random_count=16, matching=None, deadline=None):
    flattened = model.flattened()
    errors = [(instruction.args_copy()[0], instruction.targets_copy()) for instruction in flattened if instruction.type == 'error']
    declarations = stim.DetectorErrorModel()
    for instruction in flattened:
        if instruction.type != 'error':
            declarations.append(instruction)
    predictions = []
    random = np.random.default_rng(781)
    weights = np.array([np.log((1-probability)/probability) for probability, _ in errors])
    settings = [(1, 0), (1.5, 0), (.75, 0)] + [(1, .7)] * random_count
    if model.num_detectors <= 400:
        settings.append((.5, 0))
    last_time = 0
    for index, (exponent, spread) in enumerate(settings):
        if deadline is not None and index > 1 and time.monotonic() + 1.4 * last_time > deadline:
            break
        start = time.monotonic()
        perturbed = np.maximum(.01, weights * exponent + random.normal(size=len(weights)) * spread)
        if index == 0:
            current = matching if matching is not None else pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
        else:
            modified = declarations.copy()
            for probability, (_, targets) in zip(1 / (1 + np.exp(perturbed)), errors):
                modified.append('error', probability, targets)
            current = pymatching.Matching.from_detector_error_model(modified, enable_correlations=True)
        predictions.append(current.decode_batch(syndromes, enable_correlations=True)[:, 0])
        if exponent == 1 and spread == 0:
            predictions.append(current.decode_batch(syndromes)[:, 0])
        last_time = time.monotonic() - start
    return np.array(predictions)
