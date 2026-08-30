import json
import math
import time
from fractions import Fraction
from pathlib import Path

import mpmath as mp
import numpy as np

from target_method import fft_complementary_polynomial, phase_guard_margin, qsp_phase_factors

CONFIGURATIONS = [(resolution, gauge) for resolution in (4096, 8192, 16384) for gauge in (0, 1)]


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def finite(value):
    raise ValueError("nonfinite JSON constant")


def coefficients(data):
    if type(data) is not list or not 1 <= len(data) <= 256:
        raise ValueError("coefficient array length")
    values = []
    for pair in data:
        if type(pair) is not list or len(pair) != 2 or any(type(value) not in (int, float) for value in pair):
            raise ValueError("complex coefficients must be finite numeric pairs")
        converted = [float(value) for value in pair]
        if any(not math.isfinite(value) or abs(value) > 2 for value in converted):
            raise ValueError("coefficient magnitude out of range")
        values.append(complex(*converted))
    return np.array(values, dtype=np.complex128)


def exact_residual(polynomial, complement, target=Fraction(1)):
    arrays = [np.asarray(polynomial), np.asarray(complement)]
    ratios = [[(float(value.real).as_integer_ratio(), float(value.imag).as_integer_ratio()) for value in array] for array in arrays]
    exponent = max(denominator.bit_length() - 1 for array in ratios for pair in array for _, denominator in pair)
    integers = [[(real[0] << (exponent - (real[1].bit_length() - 1)), imag[0] << (exponent - (imag[1].bit_length() - 1))) for real, imag in array] for array in ratios]
    constant = sum(real * real + imag * imag for array in integers for real, imag in array)
    off_diagonal = 0
    for lag in range(1, max(map(len, integers))):
        real_sum = 0
        imag_sum = 0
        for array in integers:
            for index in range(len(array) - lag):
                left_real, left_imag = array[index + lag]
                right_real, right_imag = array[index]
                real_sum += left_real * right_real + left_imag * right_imag
                imag_sum += left_imag * right_real - left_real * right_imag
        off_diagonal += 2 * (abs(real_sum) + abs(imag_sum))
    denominator = 1 << (2 * exponent)
    return abs(Fraction(constant, denominator) - target) + Fraction(off_diagonal, denominator)


def reconstructed_error(polynomial, complement, angles, digits=80):
    with mp.workdps(digits):
        theta, phi, lambd = angles
        angle = mp.mpf(float(theta[0]))
        phase = mp.mpf(float(phi[0]))
        initial = mp.mpf(float(lambd))
        top = [mp.exp(1j * (phase + initial)) * mp.cos(angle)]
        bottom = [mp.exp(1j * initial) * mp.sin(angle)]
        for index in range(1, len(theta)):
            cosine = mp.cos(mp.mpf(float(theta[index])))
            sine = mp.sin(mp.mpf(float(theta[index])))
            rotation_phase = mp.exp(1j * mp.mpf(float(phi[index])))
            shifted = [mp.mpc(0)] + top
            padded = bottom + [mp.mpc(0)]
            top = [rotation_phase * (cosine * upper + sine * lower) for upper, lower in zip(shifted, padded)]
            bottom = [sine * upper - cosine * lower for upper, lower in zip(shifted, padded)]
        target = [mp.mpc(float(value.real), float(value.imag)) for value in np.concatenate((polynomial, complement))]
        actual = top + bottom
        overlap = sum(mp.conj(expected) * obtained for expected, obtained in zip(target, actual))
        common_phase = overlap / abs(overlap) if overlap else mp.mpc(1)
        residuals = [abs(obtained - common_phase * expected) ** 2 for expected, obtained in zip(target, actual)]
        return float(mp.sqrt(sum(residuals))), float(mp.sqrt(sum(residuals[:len(top)])))


def audit_pair(polynomial, digits=80):
    records = []
    for resolution, gauge in CONFIGURATIONS:
        transformed = polynomial.copy()
        if gauge:
            transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
        complement = fft_complementary_polynomial(transformed, tolerance=0, num_modes=resolution)
        if not np.all(np.isfinite(complement)):
            raise ValueError("completion returned nonfinite coefficients")
        residual = exact_residual(transformed, complement)
        angles = qsp_phase_factors(transformed, complement)
        margin = phase_guard_margin(transformed, complement, angles[0], angles[1])
        error, block_error = reconstructed_error(transformed, complement, angles, digits)
        records.append({"num_modes": resolution, "gauge": gauge, "completion_residual_bound": float(residual),
                        "phase_guard_margin": margin, "rms_error": error, "top_block_error": block_error,
                        "completion_valid": residual <= Fraction(1, 10**12), "guard_valid": margin >= 1e-8})
    return records


def evaluate(submission):
    started = time.monotonic()
    try:
        artifact = submission / "counterexample.json"
        if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 65536:
            raise ValueError("missing, linked or oversized counterexample.json")
        data = json.loads(artifact.read_text(), object_pairs_hook=unique, parse_constant=finite)
        if type(data) is not dict or set(data) != {"P", "H"}:
            raise ValueError("expected exactly P and H")
        polynomial, certificate = coefficients(data["P"]), coefficients(data["H"])
        degree = len(polynomial) - 1
        if not 8 <= degree <= 14 or len(certificate) != len(polynomial):
            raise ValueError("degree must be 8 through 14; certificate length must match")
        energy = float(np.vdot(polynomial, polynomial).real)
        if not 0.08 <= energy <= 0.30:
            raise ValueError("coefficient energy outside [0.08,0.30]")
        rms = math.sqrt(energy / len(polynomial))
        if np.any(np.abs(polynomial) < 0.25 * rms) or np.any(np.abs(polynomial) > 4 * rms):
            raise ValueError("coefficient density constraints fail")
        if abs(np.sum(polynomial * polynomial)) > 0.8 * energy:
            raise ValueError("polynomial is insufficiently complex")
        norm_bound = exact_residual(polynomial, certificate, Fraction(16, 25))
        if norm_bound > Fraction(1, 10**12):
            raise ValueError("whole-circle contraction certificate fails")
        records = audit_pair(polynomial)
        admissible = all(record["completion_valid"] and record["guard_valid"] for record in records)
        minimum = min(record["rms_error"] for record in records)
        core = min(1.0, minimum / 0.05) if admissible else 0.0
        passed = admissible and minimum >= 0.05
        return {"core_score": core, "worst_family_score": core, "resource_score": 1.0,
                "minimum_rms_error": minimum, "input_valid": True, "admissible": admissible,
                "valid": passed, "passed": passed, "degree": degree, "energy": energy,
                "contraction_residual_bound": float(norm_bound), "configurations": records,
                "runtime_seconds": time.monotonic() - started,
                "reason": "robust silent compiler failure certified" if passed else
                          "all-six error threshold unmet" if admissible else "completion or phase-guard requirements fail"}
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError, AssertionError) as error:
        return {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
                "valid": False, "passed": False, "input_valid": False, "reason": str(error),
                "runtime_seconds": time.monotonic() - started}
