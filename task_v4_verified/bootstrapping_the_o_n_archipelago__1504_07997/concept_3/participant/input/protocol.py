"""Public strict JSONL protocol shared by evaluator and training tools."""

import json
import math

try:
    from .model import BUDGET, FAMILIES, SCALES, TARGETS, TIME_RANGE, VERSION
except ImportError:
    from model import BUDGET, FAMILIES, SCALES, TARGETS, TIME_RANGE, VERSION


MAX_LINE_BYTES = 16384


class ProtocolError(ValueError):
    pass


def reject_constant(value):
    raise ProtocolError("non-finite JSON constant")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate JSON key")
        result[key] = value
    return result


def loads(line):
    try:
        result = json.loads(
            line, parse_constant=reject_constant, object_pairs_hook=unique_object,
        )
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProtocolError("malformed JSON") from error
    if not isinstance(result, dict):
        raise ProtocolError("message must be an object")
    return result


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError("expected a finite JSON number")
    try:
        result = float(value)
    except (ValueError, OverflowError) as error:
        raise ProtocolError("number outside finite range") from error
    if not math.isfinite(result):
        raise ProtocolError("number outside finite range")
    return result


def exact_keys(message, keys):
    if set(message) != set(keys):
        raise ProtocolError("unexpected or missing keys")


def query(message):
    exact_keys(message, ("type", "t", "u"))
    if message["type"] != "measure":
        raise ProtocolError("expected measure")
    time = number(message["t"])
    if not TIME_RANGE[0] <= time <= TIME_RANGE[1]:
        raise ProtocolError("t outside allowed range")
    if not isinstance(message["u"], list) or len(message["u"]) != 2:
        raise ProtocolError("u must contain two numbers")
    probe = [number(value) for value in message["u"]]
    if abs(math.hypot(*probe) - 1.0) > 1e-6:
        raise ProtocolError("u must be a unit vector")
    return time, probe


def answer(message):
    exact_keys(message, ("type", "estimate", "radius90"))
    if message["type"] != "answer":
        raise ProtocolError("expected answer")
    for key in ("estimate", "radius90"):
        if not isinstance(message[key], dict):
            raise ProtocolError("answer entries must be objects")
        exact_keys(message[key], TARGETS)
    estimate = [number(message["estimate"][key]) for key in TARGETS]
    radii = [number(message["radius90"][key]) for key in TARGETS]
    if any(abs(value) > 1e6 for value in estimate):
        raise ProtocolError("estimate magnitude exceeds 1e6")
    if not -math.pi / 2 <= estimate[-1] < math.pi / 2:
        raise ProtocolError("theta0 must be canonical in [-pi/2, pi/2)")
    if any(not 1e-6 <= radius <= 100 for radius in radii):
        raise ProtocolError("radius90 outside [1e-6,100]")
    if radii[-1] > math.pi / 2:
        raise ProtocolError("angular radius90 exceeds pi/2")
    return estimate, radii


def hello():
    return {
        "type": "hello", "version": VERSION, "budget": BUDGET,
        "t_range": list(TIME_RANGE), "probe_dimension": 2,
        "targets": list(TARGETS), "error_scales": SCALES.tolist(),
        "interval_level": 0.9, "family_mixture": list(FAMILIES),
        "noise": {"floor": 1.2e-5, "amplitude": 2.5e-4, "decay": 1.1},
    }


def dumps(message):
    return json.dumps(message, allow_nan=False, separators=(",", ":"))
