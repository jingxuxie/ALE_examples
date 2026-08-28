"""Version-1 spectral/continuous density transport and continuous sensitivities."""

import os

for thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ[thread_variable] = "1"

import argparse
import json
import math

import numpy as np
from scipy.integrate import quad, solve_ivp


RELATIVE_TOLERANCE = 5.0e-13
ABSOLUTE_TOLERANCE = 5.0e-14


def frequency_multiplicities(dimension):
    multiplicities = np.full(dimension // 2 + 1, 2.0)
    multiplicities[0] = 1.0
    if dimension % 2 == 0:
        multiplicities[-1] = 1.0
    return multiplicities


def real_spectrum(state):
    spectrum = np.fft.rfft(state - state[0])
    spectrum[0] = math.fsum(state)
    return spectrum


def spectral_transform(state, log_scales, inverse=False):
    factors = np.exp(-log_scales if inverse else log_scales)
    spectrum = factors * real_spectrum(state)
    return np.fft.irfft(spectrum, n=state.size), spectrum


def activation(state):
    hyperbolic = np.tanh(state)
    exponential = np.exp(-2.0 * np.abs(state))
    derivative = 4.0 * exponential / (1.0 + exponential) ** 2
    derivative = np.where(np.abs(state) <= 1.0, 1.0 - hyperbolic**2, derivative)
    return hyperbolic, derivative


def forcing_integrals(rate, duration, end):
    complex_rate = complex(rate, -1.0)
    argument = complex_rate * duration
    exponential_minus_one = np.expm1(argument)
    integral = exponential_minus_one / complex_rate
    if abs(argument) < 1.0e-3:
        term = complex(0.5 * duration**2)
        rate_derivative = term
        for order in range(1, 10):
            term *= argument * (order + 1) / (order * (order + 2))
            rate_derivative += term
    else:
        rate_derivative = (
            argument * np.exp(argument) - exponential_minus_one
        ) / complex_rate**2
    phase = complex(math.cos(end), math.sin(end))
    return (phase * integral).imag, (phase * rate_derivative).imag


def shift_modes(dimension):
    modes = np.exp(-2j * np.pi * np.arange(dimension // 2 + 1) / dimension)
    if dimension % 2 == 0:
        modes[-1] = -1.0
    return modes


def affine_spectrum(initial_spectrum, eigenvalues, forcing, start, end, dimension):
    spectrum = np.exp(eigenvalues * (end - start)) * initial_spectrum
    integral, unused_derivative = forcing_integrals(eigenvalues[0].real, end - start, end)
    spectrum[0] += dimension * forcing * integral
    return spectrum


def evaluate_affine_flow(case, parameters, times, steps):
    """Keep decoupled linear modes separate, including their small sensitivities."""
    inputs = np.asarray(case["x"], dtype=np.float64)
    cotangent = np.asarray(case["cotangent"], dtype=np.float64)
    density_weight = float(case["density_weight"])
    dimension = inputs.size
    linear, nonlinear, forcing, coupling = parameters[:4]
    log_scales = parameters[4:]
    inverse = case["direction"] == "inverse"
    start, end = times[::-1] if inverse else times
    duration = end - start
    multiplicities = frequency_multiplicities(dimension)
    modes = shift_modes(dimension)
    eigenvalues = linear + coupling * modes
    propagator = np.exp(eigenvalues * duration)
    factors = np.exp(-log_scales if inverse else log_scales)
    input_spectrum = real_spectrum(inputs)
    cotangent_spectrum = real_spectrum(cotangent)
    initial_spectrum = input_spectrum if inverse else factors * input_spectrum
    final_cotangent = factors * cotangent_spectrum if inverse else cotangent_spectrum
    initial_cotangent = np.conj(propagator) * final_cotangent
    unforced_spectrum = propagator * initial_spectrum
    forcing_integral, forcing_derivative = forcing_integrals(
        linear + coupling, duration, end
    )
    final_spectrum = unforced_spectrum.copy()
    final_spectrum[0] += dimension * forcing * forcing_integral

    def spectral_dot(left, right):
        return float(np.sum(multiplicities * np.real(np.conj(left) * right)) / dimension)

    forcing_contribution = forcing * final_cotangent[0].real * forcing_derivative
    coefficient_gradient = np.array(
        [
            duration * (spectral_dot(final_cotangent, unforced_spectrum) - density_weight * dimension)
            + forcing_contribution,
            0.0,
            final_cotangent[0].real * forcing_integral,
            duration * spectral_dot(final_cotangent, modes * unforced_spectrum)
            + forcing_contribution,
        ]
    )
    if duration != 0.0:

        def nonlinear_sensitivity(fraction):
            time = start + fraction * duration
            state_spectrum = affine_spectrum(
                initial_spectrum, eigenvalues, forcing, start, time, dimension
            )
            state = np.fft.irfft(state_spectrum, n=dimension)
            hyperbolic, derivative = activation(state)
            adjoint_spectrum = np.exp(np.conj(eigenvalues) * (end - time)) * final_cotangent
            return duration * (
                spectral_dot(adjoint_spectrum, real_spectrum(hyperbolic))
                - density_weight * np.sum(derivative)
            )

        coefficient_gradient[1], unused_error = quad(
            nonlinear_sensitivity,
            0.0,
            1.0,
            epsabs=2.0e-12,
            epsrel=2.0e-12,
            points=np.linspace(0.0, 1.0, max(16, min(steps, 64)) + 1)[1:-1],
            limit=2048,
        )

    start_velocity = eigenvalues * initial_spectrum
    start_velocity[0] += dimension * forcing * math.sin(start)
    end_velocity = eigenvalues * final_spectrum
    end_velocity[0] += dimension * forcing * math.sin(end)
    time_gradient = np.array(
        [
            -spectral_dot(initial_cotangent, start_velocity) + density_weight * dimension * linear,
            spectral_dot(final_cotangent, end_velocity) - density_weight * dimension * linear,
        ]
    )
    log_determinant = float(np.dot(multiplicities, log_scales))
    density = float(case["log_density"]) - dimension * linear * duration
    if inverse:
        output_spectrum = factors * final_spectrum
        input_gradient_spectrum = initial_cotangent
        density += log_determinant
        scale_gradient = multiplicities * (
            density_weight - np.real(np.conj(cotangent_spectrum) * output_spectrum) / dimension
        )
        time_gradient = time_gradient[::-1]
    else:
        output_spectrum = final_spectrum
        input_gradient_spectrum = factors * initial_cotangent
        density -= log_determinant
        scale_gradient = multiplicities * (
            np.real(np.conj(initial_cotangent) * initial_spectrum) / dimension - density_weight
        )
    state = np.fft.irfft(output_spectrum, n=dimension)
    return {
        "state": state.tolist(),
        "log_density": density,
        "objective": float(np.dot(cotangent, state) + density_weight * density),
        "time_gradient": time_gradient.tolist(),
        "parameter_gradient": np.concatenate((coefficient_gradient, scale_gradient)).tolist(),
        "input_gradient": np.fft.irfft(input_gradient_spectrum, n=dimension).tolist(),
    }


def spectral_field(time, spectrum, coefficients, dimension, modes):
    linear, nonlinear, forcing, coupling = coefficients
    state = np.fft.irfft(spectrum, n=dimension)
    hyperbolic, derivative = activation(state)
    velocity = (
        (linear + coupling * modes) * spectrum
        + nonlinear * real_spectrum(hyperbolic)
    )
    velocity[0] += dimension * forcing * math.sin(time)
    density_rate = -linear * dimension - nonlinear * np.sum(derivative)
    return velocity, density_rate


def integration_options(duration, coefficients, dimension, auxiliary_size, steps):
    growth_bound = abs(duration) * np.sum(np.abs(coefficients[[0, 1, 3]]))
    tolerance = np.full(dimension + auxiliary_size, ABSOLUTE_TOLERANCE)
    tolerance[:dimension] *= math.exp(-growth_bound)
    return {
        "method": "DOP853",
        "rtol": RELATIVE_TOLERANCE,
        "atol": tolerance,
        "max_step": 1.0 / max(16, min(steps, 256)),
        "first_step": 1.0e-3,
    }


def integrate_transport(
    initial_state, coefficients, start, end, steps, dense=False, initial_spectrum=None
):
    if start == end:
        return initial_state.copy(), 0.0, None
    duration = end - start
    dimension = initial_state.size
    modes = shift_modes(dimension)
    if initial_spectrum is None:
        initial_spectrum = real_spectrum(initial_state)

    def dynamics(fraction, augmented):
        time = start + fraction * duration
        velocity, density_rate = spectral_field(
            time, augmented[:-1], coefficients, dimension, modes
        )
        return duration * np.concatenate((velocity, [density_rate]))

    initial = np.concatenate((initial_spectrum, [0.0]))
    solution = solve_ivp(
        dynamics,
        (0.0, 1.0),
        initial,
        dense_output=dense,
        **integration_options(duration, coefficients, initial_spectrum.size, 1, steps),
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    return (
        np.fft.irfft(solution.y[:-1, -1], n=dimension),
        float(solution.y[-1, -1].real),
        solution.sol,
    )


def continuous_pullback(
    initial_spectrum,
    trajectory,
    coefficients,
    start,
    end,
    steps,
    final_cotangent_spectrum,
    density_weight,
    dimension,
):
    """Integrate the continuous adjoint along the saved forward trajectory."""
    spectrum_size = initial_spectrum.size
    modes = shift_modes(dimension)
    multiplicities = frequency_multiplicities(dimension)
    linear, nonlinear, forcing, coupling = coefficients
    duration = end - start

    def spectral_dot(left, right):
        return float(np.sum(multiplicities * np.real(np.conj(left) * right)) / dimension)

    if start == end:
        initial_cotangent = final_cotangent_spectrum.copy()
        coefficient_gradient = np.zeros(4)
        final_spectrum = initial_spectrum
    else:

        def adjoint_dynamics(fraction, augmented):
            time = start + fraction * duration
            state_spectrum = trajectory(fraction)[:-1]
            cotangent_spectrum = augmented[:spectrum_size]
            state = np.fft.irfft(state_spectrum, n=dimension)
            cotangent = np.fft.irfft(cotangent_spectrum, n=dimension)
            hyperbolic, derivative = activation(state)
            cotangent_rate = (
                -(linear + nonlinear * derivative[0] + coupling * np.conj(modes))
                * cotangent_spectrum
                - nonlinear * real_spectrum((derivative - derivative[0]) * cotangent)
                - 2.0 * density_weight * nonlinear * real_spectrum(hyperbolic * derivative)
            )
            parameter_integrand = np.array(
                [
                    spectral_dot(cotangent_spectrum, state_spectrum) - density_weight * dimension,
                    spectral_dot(cotangent_spectrum, real_spectrum(hyperbolic))
                    - density_weight * np.sum(derivative),
                    math.sin(time) * cotangent_spectrum[0].real,
                    spectral_dot(cotangent_spectrum, modes * state_spectrum),
                ]
            )
            return duration * np.concatenate((cotangent_rate, -parameter_integrand))

        solution = solve_ivp(
            adjoint_dynamics,
            (1.0, 0.0),
            np.concatenate((final_cotangent_spectrum, np.zeros(4))),
            **integration_options(duration, coefficients, spectrum_size, 4, steps),
        )
        if not solution.success:
            raise RuntimeError(solution.message)
        initial_cotangent = solution.y[:spectrum_size, -1]
        coefficient_gradient = solution.y[spectrum_size:, -1].real
        final_spectrum = trajectory(1.0)[:-1]

    start_velocity, start_density_rate = spectral_field(
        start, initial_spectrum, coefficients, dimension, modes
    )
    end_velocity, end_density_rate = spectral_field(
        end, final_spectrum, coefficients, dimension, modes
    )
    time_gradient = np.array(
        [
            -spectral_dot(initial_cotangent, start_velocity)
            - density_weight * start_density_rate,
            spectral_dot(final_cotangent_spectrum, end_velocity) + density_weight * end_density_rate,
        ]
    )
    return initial_cotangent, coefficient_gradient, time_gradient


def evaluate_variational_flow(case, parameters, times, steps):
    """Propagate sensitivities together when a strongly growing adjoint is ill-conditioned."""
    inputs = np.asarray(case["x"], dtype=np.float64)
    cotangent = np.asarray(case["cotangent"], dtype=np.float64)
    density_weight = float(case["density_weight"])
    dimension = inputs.size
    spectrum_size = dimension // 2 + 1
    variable_count = dimension + parameters.size + 2
    linear, nonlinear, forcing, coupling = parameters[:4]
    inverse = case["direction"] == "inverse"
    start, end = times[::-1] if inverse else times
    duration = end - start
    modes = shift_modes(dimension)
    multiplicities = frequency_multiplicities(dimension)
    spectrum = real_spectrum(inputs)
    sensitivities = np.zeros((spectrum_size + 1, variable_count), dtype=np.complex128)
    sensitivities[:spectrum_size, :dimension] = np.fft.rfft(np.eye(dimension), axis=0)
    if not inverse:
        factors = np.exp(parameters[4:])
        spectrum *= factors
        sensitivities[:spectrum_size, :dimension] *= factors[:, None]
        sensitivities[:spectrum_size, dimension + 4:-2] = np.diag(spectrum)
        sensitivities[-1, dimension + 4:-2] = -multiplicities

    def density_gauge(spectrum, sensitivities, time):
        """A bounded integration-by-parts term for the density sensitivities."""
        state = np.fft.irfft(spectrum, n=dimension)
        hyperbolic, derivative = activation(state)
        velocity = (
            linear * state + nonlinear * hyperbolic + forcing * math.sin(time)
            + coupling * np.roll(state, 1)
        )
        gauge_spectrum = real_spectrum(-nonlinear * derivative * velocity / (1 + velocity**2))
        return np.sum(
            multiplicities[:, None]
            * np.real(np.conj(gauge_spectrum)[:, None] * sensitivities[:spectrum_size]),
            axis=0,
        ) / dimension

    sensitivities[-1] -= density_gauge(spectrum, sensitivities, start)
    initial_spectrum = spectrum.copy()
    initial = np.concatenate((spectrum, [0.0], sensitivities.ravel()))
    evaluation_count = 0
    evaluation_limit = 20000

    def dynamics(fraction, augmented):
        nonlocal evaluation_count
        evaluation_count += 1
        if evaluation_count > evaluation_limit:
            raise RuntimeError("Sensitivity integration evaluation limit exceeded")
        time = start + fraction * duration
        spectrum = augmented[:spectrum_size]
        sensitivities = augmented[spectrum_size + 1:].reshape(spectrum_size + 1, variable_count)
        state = np.fft.irfft(spectrum, n=dimension)
        hyperbolic, derivative = activation(state)
        hyperbolic_spectrum = real_spectrum(hyperbolic)
        velocity = (linear + coupling * modes) * spectrum + nonlinear * hyperbolic_spectrum
        velocity[0] += dimension * forcing * math.sin(time)
        density_rate = -dimension * linear - nonlinear * np.sum(derivative)
        vector = np.append(velocity, density_rate)
        state_sensitivities = np.fft.irfft(sensitivities[:spectrum_size], n=dimension, axis=0)
        products = (derivative - derivative[0])[:, None] * state_sensitivities
        product_spectra = np.fft.rfft(products - products[0], axis=0)
        product_spectra[0] = np.sum(products, axis=0)
        sensitivity_rate = np.empty_like(sensitivities)
        sensitivity_rate[:spectrum_size] = (
            (linear + nonlinear * derivative[0] + coupling * modes)[:, None]
            * sensitivities[:spectrum_size]
            + nonlinear * product_spectra
        )
        sensitivity_rate[-1] = 0.0
        sensitivity_rate[:spectrum_size, dimension] += spectrum
        sensitivity_rate[:spectrum_size, dimension + 1] += hyperbolic_spectrum
        sensitivity_rate[0, dimension + 2] += dimension * math.sin(time)
        sensitivity_rate[:spectrum_size, dimension + 3] += modes * spectrum
        sensitivity_rate[-1, dimension] -= dimension
        sensitivity_rate[-1, dimension + 1] -= np.sum(derivative)
        sensitivity_rate *= duration
        start_derivative = -vector.copy()
        end_derivative = vector.copy()
        start_derivative[0] += duration * (1 - fraction) * dimension * forcing * math.cos(time)
        end_derivative[0] += duration * fraction * dimension * forcing * math.cos(time)
        sensitivity_rate[:, -2] += end_derivative if inverse else start_derivative
        sensitivity_rate[:, -1] += start_derivative if inverse else end_derivative
        physical_velocity = np.fft.irfft(velocity, n=dimension)
        squared_velocity = physical_velocity**2
        denominator = 1 + squared_velocity
        velocity_rate = duration * (
            (linear + nonlinear * derivative) * physical_velocity
            + coupling * np.roll(physical_velocity, 1)
            + forcing * math.cos(time)
        )
        weights = physical_velocity / denominator
        weight_rate = velocity_rate * (1 - squared_velocity) / denominator**2
        state_source = real_spectrum(
            duration * 2 * nonlinear * hyperbolic * derivative / denominator
            + nonlinear * derivative * weight_rate
        )
        rate_source = real_spectrum(nonlinear * derivative * weights)
        sensitivity_rate[-1] += np.sum(
            multiplicities[:, None]
            * np.real(
                np.conj(state_source)[:, None] * sensitivities[:spectrum_size]
                + np.conj(rate_source)[:, None] * sensitivity_rate[:spectrum_size]
            ),
            axis=0,
        ) / dimension
        return np.concatenate((duration * vector, sensitivity_rate.ravel()))

    options = integration_options(duration, parameters[:4], initial.size, 0, steps)
    options["atol"][spectrum_size] = ABSOLUTE_TOLERANCE
    options["atol"][spectrum_size + 1 + spectrum_size * variable_count:] = ABSOLUTE_TOLERANCE
    absolute_tolerance = options["atol"].copy()
    solution = None
    error_message = "Sensitivity integration failed"
    for tolerance in (RELATIVE_TOLERANCE, max(RELATIVE_TOLERANCE, 1.0e-9)):
        evaluation_count = 0
        options["rtol"] = tolerance
        options["atol"] = absolute_tolerance * (tolerance / RELATIVE_TOLERANCE)
        try:
            solution = solve_ivp(dynamics, (0.0, 1.0), initial, **options)
            if solution.success:
                break
            error_message = solution.message
        except RuntimeError as error:
            error_message = str(error)
        evaluation_limit = 100000
    if solution is None or not solution.success:
        raise RuntimeError(error_message)
    spectrum = solution.y[:spectrum_size, -1]
    density_change = solution.y[spectrum_size, -1].real
    sensitivities = solution.y[spectrum_size + 1:, -1].reshape(spectrum_size + 1, variable_count)
    sensitivities[-1] += density_gauge(spectrum, sensitivities, end)
    log_determinant = float(np.dot(multiplicities, parameters[4:]))
    density = float(case["log_density"]) + density_change
    if inverse:
        factors = np.exp(-parameters[4:])
        spectrum *= factors
        sensitivities[:spectrum_size] *= factors[:, None]
        sensitivities[:spectrum_size, dimension + 4:-2] -= np.diag(spectrum)
        sensitivities[-1, dimension + 4:-2] += multiplicities
        density += log_determinant
    else:
        density -= log_determinant
    gradient = (
        np.sum(
            multiplicities[:, None]
            * np.real(np.conj(real_spectrum(cotangent))[:, None] * sensitivities[:spectrum_size]),
            axis=0,
        ) / dimension
        + density_weight * sensitivities[-1].real
    )
    if options["rtol"] > RELATIVE_TOLERANCE:
        unused_state, density_change, trajectory = integrate_transport(
            np.fft.irfft(initial_spectrum, n=dimension), parameters[:4], start, end,
            steps, dense=True, initial_spectrum=initial_spectrum,
        )
        final_spectrum = initial_spectrum if trajectory is None else trajectory(1.0)[:-1]
        spectrum = np.exp(-parameters[4:]) * final_spectrum if inverse else final_spectrum
        density = float(case["log_density"]) + density_change
        density += log_determinant if inverse else -log_determinant
        final_cotangent = real_spectrum(cotangent)
        if inverse:
            final_cotangent *= np.exp(-parameters[4:])
            gradient[dimension + 4:-2] = multiplicities * (
                density_weight - np.real(np.conj(real_spectrum(cotangent)) * spectrum) / dimension
            )
        velocity, density_rate = spectral_field(end, final_spectrum, parameters[:4], dimension, modes)
        gradient[-2 if inverse else -1] = (
            np.sum(multiplicities * np.real(np.conj(final_cotangent) * velocity)) / dimension
            + density_weight * density_rate
        )
    state = np.fft.irfft(spectrum, n=dimension)
    return {
        "state": state.tolist(),
        "log_density": float(density),
        "objective": float(np.dot(cotangent, state) + density_weight * density),
        "time_gradient": gradient[-2:].tolist(),
        "parameter_gradient": gradient[dimension:-2].tolist(),
        "input_gradient": gradient[:dimension].tolist(),
    }


def evaluate_flow(case, parameters, times, steps):
    inputs = np.asarray(case["x"], dtype=np.float64)
    cotangent = np.asarray(case["cotangent"], dtype=np.float64)
    density_weight = float(case["density_weight"])
    initial_density = float(case["log_density"])
    dimension = inputs.size
    if inputs.ndim != 1 or dimension < 3 or cotangent.shape != inputs.shape:
        raise ValueError("Invalid state or cotangent shape")
    if parameters.shape != (4 + dimension // 2 + 1,):
        raise ValueError("Invalid parameter shape")
    if case["direction"] not in ("forward", "inverse"):
        raise ValueError("Unknown flow direction")
    if parameters[1] == 0.0:
        return evaluate_affine_flow(case, parameters, times, steps)
    growth_bound = abs(times[1] - times[0]) * np.sum(np.abs(parameters[[0, 1, 3]]))
    if (
        dimension <= 128
        and growth_bound > 20.0
        and abs(parameters[3] * (times[1] - times[0])) > 8.0
    ):
        return evaluate_variational_flow(case, parameters, times, steps)

    inverse = case["direction"] == "inverse"
    coefficients = parameters[:4]
    log_scales = parameters[4:]
    multiplicities = frequency_multiplicities(dimension)
    log_determinant = float(np.dot(multiplicities, log_scales))

    if inverse:
        start, end = times[1], times[0]
        initial_state = inputs
        initial_spectrum = real_spectrum(inputs)
        final_cotangent_spectrum = np.exp(-log_scales) * real_spectrum(cotangent)
    else:
        start, end = times
        initial_state, initial_spectrum = spectral_transform(inputs, log_scales)
        final_cotangent_spectrum = real_spectrum(cotangent)

    final_state, density_change, trajectory = integrate_transport(
        initial_state, coefficients, start, end, steps, dense=True,
        initial_spectrum=initial_spectrum,
    )
    try:
        initial_cotangent, coefficient_gradient, time_gradient = continuous_pullback(
            initial_spectrum,
            trajectory,
            coefficients,
            start,
            end,
            steps,
            final_cotangent_spectrum,
            density_weight,
            dimension,
        )
    except RuntimeError:
        if dimension > 256:
            raise
        return evaluate_variational_flow(case, parameters, times, steps)

    if inverse:
        final_spectrum = initial_spectrum if trajectory is None else trajectory(1.0)[:-1]
        scaled_spectrum = np.exp(-log_scales) * final_spectrum
        state = np.fft.irfft(scaled_spectrum, n=dimension)
        density = initial_density + density_change + log_determinant
        input_gradient = np.fft.irfft(initial_cotangent, n=dimension)
        scale_gradient = multiplicities * (
            density_weight
            - np.real(np.conj(real_spectrum(cotangent)) * scaled_spectrum) / dimension
        )
        time_gradient = time_gradient[::-1]
    else:
        state = final_state
        density = initial_density + density_change - log_determinant
        input_gradient = np.fft.irfft(np.exp(log_scales) * initial_cotangent, n=dimension)
        scale_gradient = multiplicities * (
            np.real(np.conj(initial_cotangent) * initial_spectrum) / dimension
            - density_weight
        )

    return {
        "state": state.tolist(),
        "log_density": float(density),
        "objective": float(np.dot(cotangent, state) + density_weight * density),
        "time_gradient": time_gradient.tolist(),
        "parameter_gradient": np.concatenate((coefficient_gradient, scale_gradient)).tolist(),
        "input_gradient": input_gradient.tolist(),
    }


def evaluate_acceptance(case, parameters, times, steps):
    latents = np.asarray(case["latents"], dtype=np.float64)
    uniforms = np.asarray(case["uniforms"], dtype=np.float64)
    if latents.ndim != 2 or latents.shape[0] < 1 or latents.shape[1] < 3:
        raise ValueError("Invalid latent shape")
    dimension = latents.shape[1]
    if parameters.shape != (4 + dimension // 2 + 1,):
        raise ValueError("Invalid parameter shape")
    if uniforms.shape != (latents.shape[0] - 1,) or np.any(
        (uniforms <= 0.0) | (uniforms >= 1.0)
    ):
        raise ValueError("Invalid acceptance uniforms")

    coefficients = parameters[:4]
    log_scales = parameters[4:]
    log_determinant = float(np.dot(frequency_multiplicities(dimension), log_scales))
    proposals = []
    proposal_density = []
    for latent in latents:
        normal_density = -0.5 * np.dot(latent, latent) - 0.5 * dimension * math.log(
            2.0 * math.pi
        )
        initial_state, spectrum = spectral_transform(latent, log_scales)
        if coefficients[1] == 0.0:
            spectrum = affine_spectrum(
                spectrum,
                coefficients[0] + coefficients[3] * shift_modes(dimension),
                coefficients[2],
                times[0],
                times[1],
                dimension,
            )
            state = np.fft.irfft(spectrum, n=dimension)
            density_change = -dimension * coefficients[0] * (times[1] - times[0])
        else:
            state, density_change, unused_trajectory = integrate_transport(
                initial_state, coefficients, times[0], times[1], steps,
                initial_spectrum=spectrum,
            )
        proposals.append(state)
        proposal_density.append(float(normal_density - log_determinant + density_change))

    target_density = np.array(
        [-np.sum(0.25 * state**4 + 0.3 * state**2) for state in proposals]
    )
    log_weights = target_density - np.asarray(proposal_density)
    retained = 0
    retained_states = [proposals[retained].tolist()]
    log_acceptance = []
    accepted = []
    for index, uniform in enumerate(uniforms, start=1):
        log_alpha = min(0.0, float(log_weights[index] - log_weights[retained]))
        accept = math.log(uniform) < log_alpha
        if accept:
            retained = index
        log_acceptance.append(log_alpha)
        accepted.append(int(accept))
        retained_states.append(proposals[retained].tolist())

    return {
        "proposal_states": [state.tolist() for state in proposals],
        "proposal_log_density": proposal_density,
        "log_acceptance": log_acceptance,
        "accepted": accepted,
        "retained_states": retained_states,
    }


def evaluate_case(case):
    parameters = np.asarray(case["parameters"], dtype=np.float64)
    times = np.asarray(case["times"], dtype=np.float64)
    steps = int(case["steps"])
    if times.shape != (2,) or parameters.ndim != 1 or steps < 1:
        raise ValueError("Invalid integration parameters")
    if case["kind"] == "flow":
        return evaluate_flow(case, parameters, times, steps)
    if case["kind"] == "acceptance":
        return evaluate_acceptance(case, parameters, times, steps)
    raise ValueError("Unknown case kind")


def solve_request(request):
    results = {}
    for case in request["cases"]:
        try:
            result = evaluate_case(case)
            json.dumps(result, allow_nan=False)
            results[case["id"]] = result
        except Exception as error:
            results[case["id"]] = {"error": f"{type(error).__name__}: {error}"}
    return {"version": 1, "results": results}


def run_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with open(arguments.input, encoding="utf-8") as handle:
        request = json.load(handle)
    response = solve_request(request)
    with open(arguments.output, "w", encoding="utf-8") as handle:
        json.dump(response, handle, allow_nan=False)


if __name__ == "__main__":
    run_cli()
