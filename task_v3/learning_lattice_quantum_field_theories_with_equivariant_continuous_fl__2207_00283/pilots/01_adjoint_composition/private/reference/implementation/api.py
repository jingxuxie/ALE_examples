"""Version-1 differentiable spectral/ODE transport API.

The complete request, output, derivative, density, and acceptance contracts
are in ../input/spec.md. Flow parameters concatenate [a,b,c,d] and the
dimension//2+1 logarithmic real-rFFT scales. Forward means spectral scaling
followed by dx/dt=a*x+b*tanh(x)+c*sin(t)+d*roll(x,1). Inverse reverses that
composition; times always specify the forward interval. Return state,
log_density, objective, and time/parameter/input gradients of
dot(cotangent,state)+density_weight*log_density. Acceptance requests transform
standard-normal latents and use the specified quartic target and uniforms.
"""

import json
from functools import lru_cache

import jax
import jax.numpy as jnp
import numpy as np
from flax import nnx

from bijx.bijections.continuous import ContFlowRK4
from bijx.bijections.fourier import SpectrumScaling

jax.config.update("jax_enable_x64", True)


@lru_cache(maxsize=32)
def make_map(direction, steps):
    def transform(inputs, parameters, times, initial_density):
        coefficients = parameters[:4]
        scaling = SpectrumScaling(nnx.Param(jnp.exp(parameters[4:])))

        def vector_field(time, state, **kwargs):
            velocity = (
                coefficients[0] * state
                + coefficients[1] * jnp.tanh(state)
                + coefficients[2] * jnp.sin(time)
                + coefficients[3] * jnp.roll(state, 1)
            )
            divergence = coefficients[0] * state.size + coefficients[1] * jnp.sum(
                1.0 - jnp.tanh(state) ** 2
            )
            return velocity, -divergence

        flow = ContFlowRK4(
            vector_field, t_start=times[0], t_end=times[1], steps=steps
        )
        if direction == "forward":
            state, density = scaling.forward(inputs, initial_density)
            return flow.forward(state, density)
        state, density = flow.reverse(inputs, initial_density)
        return scaling.reverse(state, density)

    return jax.jit(transform)


@lru_cache(maxsize=32)
def make_gradient(direction, steps):
    transform = make_map(direction, steps)

    def objective(inputs, parameters, times, initial_density, cotangent, weight):
        state, density = transform(inputs, parameters, times, initial_density)
        value = jnp.vdot(cotangent, state) + weight * density
        return value, (state, density)

    return jax.jit(jax.value_and_grad(objective, argnums=(0, 1, 2), has_aux=True))


def as_json(value):
    return np.asarray(value).tolist()


def evaluate_case(case):
    parameters = jnp.asarray(case["parameters"], dtype=jnp.float64)
    times = jnp.asarray(case["times"], dtype=jnp.float64)
    steps = int(case["steps"])
    if case["kind"] == "flow":
        inputs = jnp.asarray(case["x"], dtype=jnp.float64)
        (objective, (state, density)), gradients = make_gradient(
            case["direction"], steps
        )(
            inputs,
            parameters,
            times,
            jnp.asarray(case["log_density"], dtype=jnp.float64),
            jnp.asarray(case["cotangent"], dtype=jnp.float64),
            jnp.asarray(case["density_weight"], dtype=jnp.float64),
        )
        return {
            "state": as_json(state),
            "log_density": as_json(density),
            "objective": as_json(objective),
            "input_gradient": as_json(gradients[0]),
            "parameter_gradient": as_json(gradients[1]),
            "time_gradient": as_json(gradients[2]),
        }
    transform = make_map("forward", steps)
    proposals = []
    proposal_density = []
    for latent in case["latents"]:
        latent = jnp.asarray(latent, dtype=jnp.float64)
        normal_density = -0.5 * jnp.sum(latent**2) - 0.5 * latent.size * jnp.log(
            2.0 * jnp.pi
        )
        state, density = transform(latent, parameters, times, normal_density)
        proposals.append(np.asarray(state))
        proposal_density.append(float(density))
    retained = 0
    retained_states = [proposals[0]]
    accepted = []
    log_acceptance = []
    target = [-float(np.sum(0.25 * state**4 + 0.3 * state**2)) for state in proposals]
    for index, uniform in enumerate(case["uniforms"], start=1):
        ratio = min(
            0.0,
            target[index]
            - proposal_density[index]
            - target[retained]
            + proposal_density[retained],
        )
        accept = bool(np.log(uniform) < ratio)
        if accept:
            retained = index
        log_acceptance.append(ratio)
        accepted.append(int(accept))
        retained_states.append(proposals[retained])
    return {
        "proposal_states": as_json(proposals),
        "proposal_log_density": proposal_density,
        "log_acceptance": log_acceptance,
        "accepted": accepted,
        "retained_states": as_json(retained_states),
    }


def solve_request(request):
    results = {}
    for case in request["cases"]:
        try:
            results[case["id"]] = evaluate_case(case)
        except Exception as error:
            results[case["id"]] = {"error": f"{type(error).__name__}: {error}"}
    return {"version": 1, "results": results}


def run_cli():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with open(arguments.input) as handle:
        request = json.load(handle)
    response = solve_request(request)
    with open(arguments.output, "w") as handle:
        json.dump(response, handle, allow_nan=False)
