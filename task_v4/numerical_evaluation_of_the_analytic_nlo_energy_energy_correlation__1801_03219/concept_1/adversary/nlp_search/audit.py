"""Private prospective NLP audit. Never modifies a model, task, or evaluator."""

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp
import numpy as np


sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
CONCEPT = OUTPUT.parents[1]
TASK = CONCEPT.parent
MODEL_PATH = CONCEPT / "champions/generation_1/model.json"
NATIVE_PATH = TASK / "authoring/native_kernel.py"
SNAPSHOT = CONCEPT / "champions/generation_1/task_snapshot"
DECODER_PATH = SNAPSHOT / "participant/workspace/model.py"
CHANNELS = ("lc", "nlc", "nf")


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


native = load_module("nlp_audit_native", NATIVE_PATH)
decoder = load_module("nlp_audit_decoder", DECODER_PATH)
raw_model = json.loads(MODEL_PATH.read_text())
frozen_model = decoder.load_model(MODEL_PATH)


def write(relative, data):
    destination = OUTPUT / relative
    text = data if isinstance(data, str) else json.dumps(data, indent=2, allow_nan=False) + "\n"
    if destination.exists():
        subprocess.run(["apply_patch"], input="*** Begin Patch\n*** Delete File: " + str(destination) + "\n*** End Patch\n", text=True, check=True, stdout=subprocess.DEVNULL)
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, stdout=subprocess.DEVNULL)


def ratio(numerator, denominator):
    return mp.mpf(numerator) / denominator


def color_transform(fundamental, adjoint, fermion):
    size = max(len(fundamental), len(adjoint), len(fermion))
    fundamental = fundamental + [mp.mpf(0)] * (size - len(fundamental))
    adjoint = adjoint + [mp.mpf(0)] * (size - len(adjoint))
    fermion = fermion + [mp.mpf(0)] * (size - len(fermion))
    return [[first + 2 * second for first, second in zip(fundamental, adjoint)], adjoint, fermion]


def polynomials(side):
    zeta_two, zeta_three = mp.zeta(2), mp.zeta(3)
    if side == "collinear":
        leading = color_transform(
            [ratio(43, 12) * zeta_two - zeta_three - ratio(8263, 1728), ratio(25, 32)],
            [-ratio(25, 12) * zeta_two + zeta_three / 2 + ratio(17683, 2700), -ratio(107, 120)],
            [-ratio(4913, 3600), ratio(53, 240)])
        subleading = color_transform(
            [-ratio(1541, 30) * zeta_two + 65 * zeta_three + ratio(18563, 2700), ratio(42109, 1200) - 21 * zeta_two],
            [ratio(213, 5) * zeta_two - ratio(101, 2) * zeta_three - ratio(26986007, 5292000), ratio(33, 2) * zeta_two - ratio(703439, 25200)],
            [-ratio(46, 3) * zeta_two + 12 * zeta_three + ratio(2987627, 330750), ratio(86501, 12600) - 4 * zeta_two])
    else:
        leading = color_transform(
            [3 * zeta_two - zeta_three + ratio(45, 16), zeta_two + ratio(17, 4), ratio(9, 4), ratio(1, 2)],
            [ratio(11, 4) * zeta_two + ratio(3, 2) * zeta_three - ratio(35, 16), zeta_two / 2 - ratio(35, 72), ratio(11, 12), mp.mpf(0)],
            [ratio(3, 4) - zeta_two, ratio(1, 18), -ratio(1, 3), mp.mpf(0)])
        subleading = color_transform(
            [-ratio(1727, 20) * zeta_two + 42 * zeta_two * mp.log(2) + ratio(121, 2) * zeta_three + ratio(3437, 96),
             47 - 19 * zeta_two, ratio(13, 2), mp.mpf(1)],
            [ratio(6347, 80) * zeta_two - 21 * zeta_two * mp.log(2) - ratio(137, 4) * zeta_three - ratio(3305, 72),
             22 * zeta_two - ratio(2011, 72), ratio(27, 8), ratio(1, 2)],
            [-ratio(1747, 120) * zeta_two + 12 * zeta_three + ratio(2099, 144),
             ratio(361, 36) - 4 * zeta_two, -ratio(1, 2), mp.mpf(0)])
    return leading, subleading


def polynomial(coefficients, argument):
    value = mp.mpf(0)
    for coefficient in reversed(coefficients):
        value = value * argument + coefficient
    return value


def geometry(coordinate):
    argument = 1 / (1 + mp.exp(-coordinate))
    complement = 1 / (1 + mp.exp(coordinate))
    side = "collinear" if coordinate < 0 else "backward"
    epsilon = argument if side == "collinear" else complement
    return argument, complement, side, epsilon, mp.log(epsilon)


def reference(coordinate, precision):
    with mp.workdps(precision):
        coordinate = mp.mpf(coordinate)
        argument, complement, side, epsilon, logarithm = geometry(coordinate)
        leading, subleading = polynomials(side)
        components = native._components(argument)
        leading_b = [polynomial(channel, logarithm) / epsilon for channel in leading]
        residual = [value - asymptotic for value, asymptotic in zip(components, leading_b)]
        return {"density": [argument * complement * value for value in components],
                "residual": residual, "lp_b": leading_b,
                "nlp_polynomial": [polynomial(channel, logarithm) for channel in subleading]}


def model_mp(coordinate):
    knots = [mp.mpf(value) for value in raw_model["knots"]]
    interval = max(0, min(sum(coordinate >= knot for knot in knots) - 1, len(knots) - 2))
    width = knots[interval + 1] - knots[interval]
    local = (2 * coordinate - knots[interval] - knots[interval + 1]) / width
    values, derivatives = [], []
    for channel in raw_model["coefficients"][interval]:
        coefficients = [mp.mpf(float(value)) for value in channel]
        previous, current = mp.mpf(1), local
        previous_derivative, current_derivative = mp.mpf(0), mp.mpf(1)
        value = coefficients[0]
        derivative = mp.mpf(0)
        if len(coefficients) > 1:
            value += coefficients[1] * current
            derivative += coefficients[1]
        for coefficient in coefficients[2:]:
            following = 2 * local * current - previous
            following_derivative = 2 * current + 2 * local * current_derivative - previous_derivative
            value += coefficient * following
            derivative += coefficient * following_derivative
            previous, current = current, following
            previous_derivative, current_derivative = current_derivative, following_derivative
        values.append(value)
        derivatives.append(2 * derivative / width)
    return values, derivatives


def reference_derivative(coordinate, precision, step_text):
    with mp.workdps(precision):
        coordinate = mp.mpf(coordinate)
        step = mp.mpf(step_text)
        samples = [reference(coordinate + offset * step, precision)["residual"] for offset in (-2, -1, 1, 2)]
        return [(samples[0][channel] - 8 * samples[1][channel] + 8 * samples[2][channel] - samples[3][channel]) / (12 * step) for channel in range(3)]


def main():
    started = time.monotonic()
    protected = [MODEL_PATH, NATIVE_PATH, DECODER_PATH, SNAPSHOT / "evaluator/evaluate.py", SNAPSHOT / "participant/TASK.md"]
    hashes = {str(path.relative_to(TASK)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    rows = []
    derivative_rows = []
    endpoint_checks = []
    with mp.workdps(280):
        for sign in (-1, 1):
            for magnitude in (30, 40, 50, 60):
                coordinate = mp.mpf(sign * magnitude)
                coarse = reference(coordinate, 200)
                fine = reference(coordinate, 280)
                _, _, side, epsilon, _ = geometry(coordinate)
                for channel, name in enumerate(CHANNELS):
                    gap = abs(fine["residual"][channel] - coarse["residual"][channel])
                    defect = abs(fine["residual"][channel] - fine["nlp_polynomial"][channel])
                    endpoint_checks.append({"side": side, "t": int(coordinate), "channel": name,
                                            "native_precision_gap": mp.nstr(gap, 24),
                                            "lp_numerator_defect": mp.nstr(epsilon * abs(fine["residual"][channel]), 24),
                                            "nlp_absolute_defect": mp.nstr(defect, 24),
                                            "nlp_scaled_defect": float(defect / (1 + abs(fine["nlp_polynomial"][channel])))})
                    if gap > mp.mpf("1e-55"):
                        raise RuntimeError("deep endpoint native precision did not resolve the residual")
        print(json.dumps({"phase": "deep_limits_validated", "checks": len(endpoint_checks)}), flush=True)
        for coordinate_float in np.concatenate((-np.arange(4.5, 24.01, .5)[::-1], np.arange(4.5, 24.01, .5))):
            coordinate = mp.mpf(float(coordinate_float))
            coarse = reference(coordinate, 160)
            fine = reference(coordinate, 220)
            argument, complement, side, epsilon, logarithm = geometry(coordinate)
            product = argument * complement
            leading, _ = polynomials(side)
            predicted, predicted_derivative = model_mp(coordinate)
            frozen = np.asarray(decoder.evaluate(frozen_model, np.array([coordinate_float])))[0]
            frozen_derivative = np.asarray(decoder.evaluate(frozen_model, np.array([coordinate_float]), True))[0]
            float_argument = math.exp(-float(np.logaddexp(0.0, -coordinate_float)))
            float_complement = math.exp(-float(np.logaddexp(0.0, coordinate_float)))
            float_log = -float(np.logaddexp(0.0, -coordinate_float if side == "collinear" else coordinate_float))
            for channel, name in enumerate(CHANNELS):
                gap = abs(fine["residual"][channel] - coarse["residual"][channel])
                if gap > mp.mpf("1e-85"):
                    raise RuntimeError("same-domain native precision did not resolve the residual")
                source = fine["residual"][channel]
                lp_density = product * fine["lp_b"][channel]
                reconstructed = (predicted[channel] - lp_density) / product
                replayed_float = (mp.mpf(float(frozen[channel])) - lp_density) / product
                float_polynomial = np.polynomial.polynomial.polyval(float_log, [float(value) for value in leading[channel]])
                float_lp_density = (float_complement if side == "collinear" else float_argument) * float_polynomial
                float_residual = (float(frozen[channel]) - float_lp_density) / (float_argument * float_complement)
                power = 1 if side == "collinear" else (2 if name == "nf" else 3)
                chart_scale = (1 + abs(logarithm))**power
                error = abs(reconstructed - source)
                rows.append({"side": side, "t": float(coordinate), "channel": name,
                             "source_F": float(fine["density"][channel]), "model_F": float(frozen[channel]),
                             "original_value_tolerance_ratio": float(abs(mp.mpf(float(frozen[channel])) - fine["density"][channel]) / (mp.mpf("2e-8") * (1 + abs(fine["density"][channel])))),
                             "source_G": float(source), "representation_G": float(reconstructed),
                             "frozen_F_exact_subtraction_G": float(replayed_float), "stable_binary64_G": float_residual,
                             "representation_abs_error_G": float(error),
                             "representation_relative_error_G": float(error / abs(source)) if source else None,
                             "representation_mixed_error_G": float(error / (1 + abs(source))),
                             "frozen_F_mixed_error_G": float(abs(replayed_float - source) / (1 + abs(source))),
                             "stable_binary64_mixed_error_G": float(abs(mp.mpf(float_residual) - source) / (1 + abs(source))),
                             "normalized_chart_error": float(error / chart_scale),
                             "condition_number_subtraction": float((abs(fine["density"][channel]) + abs(lp_density)) / abs(product * source)),
                             "inverse_prefactor": float(1 / product),
                             "density_representation_error": float(abs(predicted[channel] - fine["density"][channel])),
                             "density_float_evaluation_error": float(abs(mp.mpf(float(frozen[channel])) - predicted[channel])),
                             "stable_subtraction_arithmetic_error_G": float(abs(mp.mpf(float_residual) - replayed_float)),
                             "native_precision_gap": mp.nstr(gap, 24)})
            if abs(coordinate_float) in (6, 12, 18, 24):
                derivative_coarse = reference_derivative(coordinate, 160, "1e-10")
                derivative_fine = reference_derivative(coordinate, 220, "1e-14")
                for channel, name in enumerate(CHANNELS):
                    polynomial_value = polynomial(leading[channel], logarithm)
                    derivative_coefficients = [order * coefficient for order, coefficient in enumerate(leading[channel])][1:]
                    polynomial_derivative = polynomial(derivative_coefficients, logarithm)
                    if side == "collinear":
                        lp_density_derivative = -product * polynomial_value + complement**2 * polynomial_derivative
                    else:
                        lp_density_derivative = product * polynomial_value - argument**2 * polynomial_derivative
                    residual = (predicted[channel] - product * fine["lp_b"][channel]) / product
                    reconstructed_derivative = (predicted_derivative[channel] - lp_density_derivative) / product - (1 - 2 * argument) * residual
                    frozen_residual = (mp.mpf(float(frozen[channel])) - product * fine["lp_b"][channel]) / product
                    frozen_replayed_derivative = (mp.mpf(float(frozen_derivative[channel])) - lp_density_derivative) / product - (1 - 2 * argument) * frozen_residual
                    source_derivative = derivative_fine[channel]
                    gap = abs(source_derivative - derivative_coarse[channel])
                    if gap > mp.mpf("1e-30"):
                        raise RuntimeError("native residual derivative did not converge")
                    derivative_rows.append({"side": side, "t": float(coordinate), "channel": name,
                                            "source_G_prime": float(source_derivative),
                                            "representation_G_prime": float(reconstructed_derivative),
                                            "frozen_F_exact_subtraction_G_prime": float(frozen_replayed_derivative),
                                            "representation_abs_error": float(abs(reconstructed_derivative - source_derivative)),
                                            "representation_relative_error": float(abs(reconstructed_derivative - source_derivative) / abs(source_derivative)),
                                            "representation_mixed_error": float(abs(reconstructed_derivative - source_derivative) / (1 + abs(source_derivative))),
                                            "native_derivative_refinement_gap": mp.nstr(gap, 24)})
        groups = {}
        for side in ("collinear", "backward"):
            for name in CHANNELS:
                values = [row for row in rows if row["side"] == side and row["channel"] == name]
                derivatives = [row for row in derivative_rows if row["side"] == side and row["channel"] == name]
                groups[side + "/" + name] = {"worst_value": max(values, key=lambda row: row["representation_mixed_error_G"]),
                                              "worst_derivative": max(derivatives, key=lambda row: row["representation_mixed_error"])}
        for path in protected:
            if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[str(path.relative_to(TASK))]:
                raise RuntimeError("a protected input changed during this read-only audit")
        result = {"scope": "Prospective NLP-residual objective only. Not an original-contract failure.",
                  "definition": "G=(F-F_LP)/(z*(1-z))=B-B_LP; F_LP=(1-z)*P_left(log z) or z*P_right(log(1-z)).",
                  "champion_coefficient_count": sum(len(channel) for panel in raw_model["coefficients"] for channel in panel),
                  "champion_scalar_count": frozen_model["scalar_count"],
                  "input_sha256": hashes, "native_dps": [160, 220], "deep_native_dps": [200, 280],
                  "derivative_checks": "Five-point central stencils at h=1e-10/1e-14, 160/220 dps.",
                  "max_original_value_ratio_on_audit_grid": max(row["original_value_tolerance_ratio"] for row in rows),
                  "groups": groups, "rows": rows, "derivative_rows": derivative_rows,
                  "deep_endpoint_checks": endpoint_checks, "seconds": time.monotonic() - started,
                  "interpretation": "Representation-only errors use exact replay of the actual binary64 coefficients in high precision. Frozen-value and stable-binary64 subtraction are reported separately. No naive 1-z subtraction or log(epsilon)=-abs(t) approximation is used."}
        write("results.json", result)
        print(json.dumps({"groups": groups, "original_value_maxratio": result["max_original_value_ratio_on_audit_grid"], "seconds": result["seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
