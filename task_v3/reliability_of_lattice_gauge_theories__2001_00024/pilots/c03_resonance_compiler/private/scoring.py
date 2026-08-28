import math

import numpy as np

from physics import penalty_rows


def matrix_for(case, certificate):
    rows = penalty_rows(certificate)
    matrix = np.zeros((len(rows), case["length"]), dtype=float)
    for index, row in enumerate(rows):
        for site, value in row:
            matrix[index, site] = value
    return matrix


def validate_ticks(case, schedule, digital=False):
    ticks = schedule["ticks"]
    hardware = case["hardware"]
    if not isinstance(ticks, list) or len(ticks) != case["length"]:
        raise ValueError("one DAC tick per site required")
    if any(type(value) is not int or abs(value) > cap for value, cap in zip(ticks, hardware["caps"])):
        raise ValueError("DAC ticks outside hardware alphabet")
    if digital and (type(schedule["phase_tick"]) is not int or schedule["phase_tick"] not in hardware["phase_ticks"]):
        raise ValueError("phase_tick outside clock window")
    return np.asarray(ticks, dtype=float) / hardware["denominator"]


def evaluate_controls(case, matrix, schedule, digital=False):
    coefficients = validate_ticks(case, schedule, digital)
    hardware = case["hardware"]
    detuning = matrix @ coefficients
    uncertainty = np.abs(matrix) @ np.asarray(hardware["uncertainty"])
    if digital:
        phase = math.pi * schedule["phase_tick"] / hardware["phase_denominator"]
        gaps = np.abs((phase * detuning + math.pi) % (2 * math.pi) - math.pi)
        margins = np.maximum(0, gaps - abs(phase) * uncertainty) / math.pi
    else:
        margins = np.maximum(0, np.abs(detuning) - uncertainty) / hardware["bandwidth"]
    if not len(margins):
        raise ValueError("case has no physical departing transitions")
    minimum, mean = float(margins.min()), float(margins.mean())
    return {"quality": 0.75 * minimum + 0.25 * mean,
            "minimum_margin": minimum, "mean_margin": mean, "constraints": len(margins)}


def relative_score(value, baseline, reference):
    if not reference > baseline:
        raise ValueError("invalid frozen anchor ordering")
    normalized = (value - baseline) / (reference - baseline)
    coordinate = (2 * normalized - 1) * 9 / math.sqrt(19)
    return 0.5 * (1 + coordinate / math.hypot(1, coordinate))


def certificate_tokens(certificate, length):
    if not isinstance(certificate, list):
        raise ValueError("certificate must be a list")
    sector_tokens, joint_tokens, instances = set(), set(), set()
    for entry in certificate:
        channel, anchor = entry["channel"], entry["anchor"]
        if not isinstance(channel, str) or type(anchor) is not int or not 0 <= anchor < length:
            raise ValueError("invalid instance key")
        instance = (channel, anchor)
        if instance in instances:
            raise ValueError("duplicate channel instance")
        instances.add(instance)
        transfers = entry["transfers"]
        if not isinstance(transfers, list):
            raise ValueError("transfers must be a list")
        if not transfers:
            sector_tokens.add((instance, ()))
            joint_tokens.add((instance, (), ()))
        for transfer in transfers:
            vectors = []
            for name in ("sector", "penalty"):
                vector = transfer[name]
                if not isinstance(vector, list):
                    raise ValueError("sparse vector must be a list")
                previous = -1
                pairs = []
                for pair in vector:
                    if not isinstance(pair, list) or len(pair) != 2:
                        raise ValueError("invalid sparse pair")
                    site, value = pair
                    if type(site) is not int or not previous < site < length:
                        raise ValueError("sparse indices must increase and be in range")
                    if type(value) is not int or value == 0:
                        raise ValueError("sparse values must be nonzero integers")
                    pairs.append((site, value))
                    previous = site
                vectors.append(tuple(pairs))
            sector, penalty = vectors
            if not sector:
                raise ValueError("gauge-preserving row is not a departure")
            sector_tokens.add((instance, sector))
            joint_tokens.add((instance, sector, penalty))
    return sector_tokens, joint_tokens


def f1(expected, observed):
    return 2 * len(expected & observed) / (len(expected) + len(observed)) if expected or observed else 1.0


def score_answer(case, expected, answer, anchors):
    if not isinstance(answer, dict):
        answer = {}
    errors = []
    truth_sector, truth_joint = certificate_tokens(expected, case["length"])
    try:
        got_sector, got_joint = certificate_tokens(answer.get("certificate"), case["length"])
        sector_f1, transfer_f1 = f1(truth_sector, got_sector), f1(truth_joint, got_joint)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        sector_f1, transfer_f1 = 0.0, 0.0
        errors.append("certificate: " + str(error))
    result = {"sector_f1": sector_f1, "transfer_f1": transfer_f1,
              "algebra": (sector_f1 + transfer_f1) / 2}
    matrix = matrix_for(case, expected)
    for name in ("analog", "digital"):
        try:
            quality = evaluate_controls(case, matrix, answer[name], digital=name == "digital")
            quality["score"] = relative_score(quality["quality"], anchors[name]["weak"], anchors[name]["strong"])
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            quality = {"score": 0.0, "quality": None, "minimum_margin": None, "mean_margin": None}
            errors.append(name + ": " + str(error))
        result[name] = quality
    result["score"] = (result["algebra"] * result["analog"]["score"] * result["digital"]["score"]) ** (1 / 3)
    result["errors"] = errors
    return result
