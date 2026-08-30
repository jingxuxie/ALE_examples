import hashlib
import json
import random
from fractions import Fraction
from pathlib import Path

import mpmath as mp


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator" / "hidden"
DIGITS = 290
FAMILIES = ("separated", "near_coincident", "multiscale", "boundary_isolated", "rotating_null", "coupled_high_order")


def rational(value):
    return Fraction(str(value))


def add(left, right):
    output = [Fraction(0)] * max(len(left), len(right))
    for index, coefficient in enumerate(left):
        output[index] += coefficient
    for index, coefficient in enumerate(right):
        output[index] += coefficient
    while len(output) > 1 and output[-1] == 0:
        output.pop()
    return output


def scale(polynomial, factor):
    return [coefficient * factor for coefficient in polynomial]


def multiply(left, right):
    output = [Fraction(0)] * (len(left) + len(right) - 1)
    for left_index, left_value in enumerate(left):
        for right_index, right_value in enumerate(right):
            output[left_index + right_index] += left_value * right_value
    return output


def decimal(value):
    value = Fraction(value)
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ValueError("nonterminating rational")
    digits = max(twos, fives)
    numerator = value.numerator * 2 ** (digits - twos) * 5 ** (digits - fives)
    sign = "-" if numerator < 0 else ""
    text = str(abs(numerator)).zfill(digits + 1)
    if digits:
        text = (text[:-digits] + "." + text[-digits:]).rstrip("0").rstrip(".")
    return sign + text


def number(value):
    if isinstance(value, Fraction):
        return mp.mpf(value.numerator) / value.denominator
    return mp.mpf(value)


def text(value, digits=260):
    return mp.nstr(value, digits)


def evaluate(polynomial, position):
    result = mp.mpf(0)
    for coefficient in reversed(polynomial):
        result = result * position + number(coefficient)
    return result


def chebyshev(polynomial):
    result = [Fraction(0)] * len(polynomial)
    power = [Fraction(1)]
    for index, coefficient in enumerate(polynomial):
        for degree, value in enumerate(power):
            result[degree] += coefficient * value
        following = [Fraction(0)] * (len(power) + 1)
        for degree, value in enumerate(power):
            if degree == 0:
                following[1] += value
            else:
                following[degree - 1] += value / 2
                following[degree + 1] += value / 2
        power = following
    return result


def pack(polynomials):
    transformed = [chebyshev(polynomial) for polynomial in polynomials]
    return [[decimal(polynomial[degree] if degree < len(polynomial) else 0)
             for polynomial in transformed] for degree in range(max(map(len, transformed)))]


def matrix_multiply(left, right):
    return [[add(multiply(left[row][0], right[0][column]),
                 multiply(left[row][1], right[1][column]))
             for column in range(2)] for row in range(2)]


def jacobi(size, family, variant, branch, rng):
    diagonal = [rational("-0.76") + rational("1.44") * Fraction(index, size - 1)
                + rational("0.001") * rng.randint(-6, 6) + branch * rational("0.071")
                for index in range(size)]
    diagonal = [Fraction(round(value * 10 ** 9), 10 ** 9) for value in diagonal]
    offdiagonal = [rational("0.001") * rng.randint(2, 8) for _ in range(size - 1)]
    if family in ("near_coincident", "rotating_null", "coupled_high_order"):
        exponent = {"near_coincident": 6 + 2 * variant,
                    "rotating_null": 5 + 2 * variant,
                    "coupled_high_order": 4 + variant}[family]
        gap = Fraction(1, 10 ** exponent)
        center = rational("-0.15") if branch == 0 else rational("0.27")
        clustered = min(size, 3 if branch == 0 else 2)
        for index in range(clustered):
            diagonal[index] = center + (index - 1) * gap
        for index in range(min(clustered, size - 1)):
            offdiagonal[index] = gap * rational("0.13")
    if family == "boundary_isolated":
        gap = Fraction(1, 10 ** (7 + 2 * variant))
        diagonal[0] = -1 + gap * (1 + 3 * branch)
        offdiagonal[0] = gap * rational("0.04")
    older = [Fraction(1)]
    current = [-diagonal[0], Fraction(1)]
    for index in range(1, size):
        following = add(multiply(current, [-diagonal[index], Fraction(1)]),
                        scale(older, -offdiagonal[index - 1] ** 2))
        older, current = current, following
    matrix = mp.matrix(size)
    for index, value in enumerate(diagonal):
        matrix[index, index] = number(value)
    for index, value in enumerate(offdiagonal):
        matrix[index, index + 1] = matrix[index + 1, index] = number(value)
    eigenvalues = list(mp.eigsy(matrix, eigvals_only=True))
    assert all(-1 < value < 1 for value in eigenvalues)
    assert max(abs(evaluate(current, value)) for value in eigenvalues) < mp.mpf("1e-270")
    return current, eigenvalues, {"diagonal": list(map(decimal, diagonal)), "offdiagonal": list(map(decimal, offdiagonal))}


def continuum(block_id, family, variant, rng, auxiliary=False):
    actual_family = "separated" if auxiliary and family != "coupled_high_order" else family
    if auxiliary:
        sizes = (4, 3) if family == "coupled_high_order" else (2, 2)
    else:
        sizes = (7 + variant, 6) if family == "coupled_high_order" else (4 + variant, 3)
    polynomials = []
    roots = []
    certificates = []
    for branch, size in enumerate(sizes):
        polynomial, eigenvalues, certificate = jacobi(size, actual_family, variant, branch, rng)
        factor = multiply(polynomial, polynomial)
        if family == "coupled_high_order" and variant == 2 and branch == 0 and not auxiliary:
            factor = multiply(factor, factor)
        center = rational("0.113") + branch * rational("0.319")
        width = Fraction(1, 10 ** (8 + 4 * variant))
        positive = [center ** 2 + width ** 2, -2 * center, Fraction(1)]
        factor = multiply(factor, positive)
        boundary = None
        if family == "boundary_isolated" and not auxiliary:
            boundary = -1 if branch == 0 else 1
            factor = multiply(factor, [Fraction(1), Fraction(1 if branch == 0 else -1)])
            eigenvalues.append(mp.mpf(boundary))
        amplitude = Fraction(1)
        if family == "multiscale":
            amplitude = Fraction(1, 10 ** (8 + 8 * variant)) if branch == 0 else Fraction(10 ** (8 + 6 * variant))
        factor = scale(factor, amplitude)
        polynomials.append(factor)
        roots.append(eigenvalues)
        certificates.append({"jacobi": certificate, "positive_center": decimal(center),
                             "positive_width": decimal(width), "boundary": boundary,
                             "amplitude": decimal(amplitude), "power_coefficients": list(map(decimal, factor))})
    angle = [rational("0.23"), rational("0.41"), rational("-0.17")]
    if family == "rotating_null" and not auxiliary:
        inverse_gap = 10 ** (5 + 2 * variant)
        angle = [rational("0.15") * inverse_gap, Fraction(inverse_gap)]
    rotation = [[[Fraction(1)], angle], [scale(angle, -1), [Fraction(1)]]]
    constant = [[[rational("1.13")], [rational("0.17")]], [[rational("-0.2")], [Fraction(1)]]]
    shear = [[[Fraction(1)], [Fraction(0), Fraction(0), rational("0.07")]], [[Fraction(0)], [Fraction(1)]]]
    transform = matrix_multiply(matrix_multiply(rotation, constant), shear)
    entries = []
    for row, column in ((0, 0), (0, 1), (1, 1)):
        entries.append(add(multiply(polynomials[0], multiply(transform[0][row], transform[0][column])),
                           multiply(polynomials[1], multiply(transform[1][row], transform[1][column]))))
    origin = rational("2.5") + variant + (20 if auxiliary else 0)
    coordinate_scale = rational("1.25")
    if family == "multiscale":
        origin = Fraction(10 ** (3 + 3 * variant)) + (20 if auxiliary else 0)
        coordinate_scale = Fraction(1, 10 ** (2 + 3 * variant))
    global_scale = Fraction(10 ** 40) if auxiliary and family == "multiscale" else Fraction(1)
    block = {"id": block_id, "kind": "interval", "origin": decimal(origin), "scale": decimal(coordinate_scale),
             "matrix": pack([scale(entry, global_scale) for entry in entries])}
    features = []
    for branch, eigenvalues in enumerate(roots):
        for position in eigenvalues:
            transform_at = [[evaluate(entry, position) for entry in row] for row in transform]
            if branch == 0:
                vector = [transform_at[1][1], -transform_at[1][0]]
            else:
                vector = [-transform_at[0][1], transform_at[0][0]]
            norm_squared = sum(value ** 2 for value in vector)
            projector = [vector[0] ** 2 / norm_squared, vector[0] * vector[1] / norm_squared, vector[1] ** 2 / norm_squared]
            features.append({"block": block_id, "t": position, "x": number(origin) + number(coordinate_scale) * position,
                             "projector": projector})
    certificate = {"branches": certificates, "global_scale": decimal(global_scale),
                   "transform": [[list(map(decimal, entry)) for entry in row] for row in transform]}
    return block, features, certificate


def point(block_id, variant, singular, tiny=False):
    direction = [rational("0.7"), rational("-0.4")]
    other = [direction[1], -direction[0]]
    lift = Fraction(0) if singular else Fraction(1, 10 ** 36) if tiny else Fraction(2)
    entries = [other[0] ** 2 + lift * direction[0] ** 2,
               other[0] * other[1] + lift * direction[0] * direction[1],
               other[1] ** 2 + lift * direction[1] ** 2]
    block = {"id": block_id, "kind": "point", "origin": str(40 + variant), "scale": "1",
             "matrix": [[decimal(entry) for entry in entries]]}
    features = []
    if singular:
        norm_squared = sum(value ** 2 for value in direction)
        features.append({"block": block_id, "t": mp.mpf(0), "x": mp.mpf(40 + variant),
                         "projector": [number(direction[0] ** 2 / norm_squared),
                                       number(direction[0] * direction[1] / norm_squared),
                                       number(direction[1] ** 2 / norm_squared)]})
    return block, features, {"point_lift": decimal(lift)}


def kernel_value(coefficients, position, projector):
    previous, current = mp.mpf(1), position
    result = mp.mpf(0)
    for degree, packed in enumerate(coefficients):
        if degree == 0:
            basis = previous
        elif degree == 1:
            basis = current
        else:
            previous, current = current, 2 * position * current - previous
            basis = current
        result += basis * (number(packed[0]) * projector[0] + 2 * number(packed[1]) * projector[1] + number(packed[2]) * projector[2])
    return result


def make_case(family, variant, seed):
    rng = random.Random(seed)
    blocks, features, proofs = [], [], {}
    for auxiliary in (False, True):
        block, found, proof = continuum("b" + str(len(blocks)), family, variant, rng, auxiliary)
        blocks.append(block)
        features.extend(found)
        proofs[block["id"]] = proof
    if family == "boundary_isolated":
        for singular, tiny in ((True, False), (False, False), (False, True)):
            block, found, proof = point("b" + str(len(blocks)), variant, singular, tiny)
            blocks.append(block)
            features.extend(found)
            proofs[block["id"]] = proof
    low, high = (-12, 10) if family in ("multiscale", "coupled_high_order") else (-4, 4)
    for index, feature in enumerate(features):
        exponent = low + (index * 7 + variant * 3) % (high - low + 1)
        feature["weight"] = number(Fraction(10) ** exponent * Fraction(rng.randint(11, 29), 10))
    for block in blocks:
        degree = 0 if block["kind"] == "point" else 16
        block["moments"] = [
            [[decimal(Fraction(rng.randint(-6, 6), 2 ** (power + 2))) for _ in range(3)]
             for power in range(degree + 1)] for _ in range(40)
        ]
    by_id = {block["id"]: block for block in blocks}
    rhs = []
    for row in range(40):
        value = mp.fsum(feature["weight"] * kernel_value(by_id[feature["block"]]["moments"][row], feature["t"], feature["projector"])
                        for feature in features)
        rhs.append(text(value, 240))
    serialized_features = [{key: [text(entry) for entry in value] if isinstance(value, list)
                            else value if key == "block" else text(value)
                            for key, value in feature.items()} for feature in features]
    case = {"version": 1, "blocks": blocks, "rhs": rhs}
    witness = {"family": family, "variant": variant, "seed": seed, "features": serialized_features, "certificate": proofs}
    return case, witness


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    mp.mp.dps = DIGITS
    manifest = {"version": 1, "cases": []}
    for family_index, family in enumerate(FAMILIES):
        for variant in range(3):
            seed = 150407997 + 7919 * family_index + 104729 * variant
            case, witness = make_case(family, variant, seed)
            token = hashlib.sha256((str(seed) + "mixed-matrix-v1").encode()).hexdigest()[:16]
            input_path = HIDDEN / "challenges" / (token + ".json")
            witness_path = HIDDEN / "witnesses" / (token + ".json")
            write_json(input_path, case)
            write_json(witness_path, witness)
            manifest["cases"].append({"id": token, "family": family,
                                      "input": str(input_path.relative_to(ROOT)),
                                      "witness": str(witness_path.relative_to(ROOT)),
                                      "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest()})
    write_json(HIDDEN / "manifest.json", manifest)
    for index, family in enumerate(("separated", "boundary_isolated"), 1):
        case, witness = make_case(family, 0, 87123 + index)
        write_json(ROOT / "participant" / "input" / ("sample_%02d.json" % index), case)
        write_json(HIDDEN / "witnesses" / ("sample_%02d.json" % index), witness)
    print(json.dumps({"generated_cases": len(manifest["cases"]), "samples": 2}))


if __name__ == "__main__":
    main()
