"""Independent numerical checks for the self-contained solver."""

import copy
import json
from pathlib import Path
import tempfile
import time

import solve
import numpy as np
from scipy.integrate import solve_ivp


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent/"participant"/"input"/"example.json"


def independent_noise(case, materials):
    count = len(materials)
    nfft = case["nfft"]
    coarse_dt = case["dt"]*case["decimation"]
    frequencies = 2*np.pi*np.arange(nfft//2+1)/(nfft*coarse_dt)
    powers = []
    for material in case["materials"]:
        strength, gamma, omega, temperature = [material[key] for key in ("A", "Gamma", "omega0", "T")]
        if case["thermostat"] == "classical":
            numerator = np.full_like(frequencies, 2*temperature)
        elif temperature == 0:
            numerator = frequencies.copy() if case["thermostat"] == "quantum" else np.zeros_like(frequencies)
        else:
            numerator = np.empty_like(frequencies)
            numerator[0] = 2*temperature
            numerator[1:] = frequencies[1:]/np.tanh(frequencies[1:]/(2*temperature))
            if case["thermostat"] == "nozero":
                numerator[1:] -= frequencies[1:]
        powers.append(strength*gamma*numerator/((omega**2-frequencies**2)**2+gamma**2*frequencies**2))
    powers = np.asarray(powers)
    white = np.random.default_rng(case["noise_seed"]).standard_normal((count, 3, nfft))
    noise = np.fft.irfft(np.fft.rfft(white, axis=-1)*np.sqrt(2*powers[materials, None, :]/coarse_dt), n=nfft, axis=-1)
    multiplicities = np.full(len(frequencies), 2.0)
    multiplicities[0] = 1
    if nfft % 2 == 0:
        multiplicities[-1] = 1
    phase = 2*np.pi*np.arange(len(frequencies))[:, None]*np.asarray(case["lags"])[None, :]/nfft
    covariance = (2*powers/coarse_dt*multiplicities) @ np.cos(phase)/nfft
    return noise, covariance


def reference(case):
    spins, materials, neighbors, parameters = solve.initialize(case)
    count = len(spins)
    mu, anisotropy, strength, omega, gamma, temperature = parameters[materials].T
    noise, covariance = independent_noise(case, materials)
    exchange = np.asarray(case["exchange"])[materials[:, None], materials[neighbors]]
    coarse_dt = case["dt"]*case["decimation"]
    memory = np.zeros((count, 3))
    if case["initial_memory"] == "equilibrated":
        memory = strength[:, None]*spins/omega[:, None]**2
    state = np.concatenate((spins.ravel(), memory.ravel(), np.zeros(count*3)))
    trace = np.empty((len(case["sample_steps"]), len(parameters), 3))

    def derivative(time_value, values):
        current = values[:count*3].reshape(count, 3)
        displacement = values[count*3:count*6].reshape(count, 3)
        velocity = values[count*6:].reshape(count, 3)
        fractional = time_value/coarse_dt
        knot = int(np.floor(fractional))
        fraction = fractional-knot
        bath = (1-fraction)*noise[:, :, knot % case["nfft"]]+fraction*noise[:, :, (knot+1) % case["nfft"]]
        field = np.asarray(case["field"])+np.sum(exchange[:, :, None]*current[neighbors], axis=1)/mu[:, None]
        field[:, 2] += 2*anisotropy*current[:, 2]/mu
        spin_rate = np.cross(current, field+bath/np.sqrt(mu[:, None])+displacement)
        acceleration = strength[:, None]*current-omega[:, None]**2*displacement-gamma[:, None]*velocity
        return np.concatenate((spin_rate.ravel(), velocity.ravel(), acceleration.ravel()))

    boundaries = sorted(set(range(0, case["steps"]+1, case["decimation"])) | set(case["sample_steps"]) | {case["steps"]})
    previous = 0
    for step in boundaries:
        if step > previous:
            integrated = solve_ivp(derivative, (previous*case["dt"], step*case["dt"]), state,
                                   method="DOP853", rtol=2e-12, atol=2e-13)
            assert integrated.success, integrated.message
            state = integrated.y[:, -1]
        for snapshot, sampled in enumerate(case["sample_steps"]):
            if sampled == step:
                for species in range(len(parameters)):
                    trace[snapshot, species] = state[:count*3].reshape(count, 3)[materials == species].mean(axis=0)
        previous = step
    return dict(spins=state[:count*3].reshape(count, 3),
                memory=np.column_stack((state[count*3:count*6].reshape(count, 3), state[count*6:].reshape(count, 3))),
                trace=trace, covariance=covariance)


def variants():
    with open(PUBLIC) as source:
        example = json.load(source)
    example["shape"] = [3, 3, 2]
    example["sample_steps"] = [0, 1, 11, 48, 93, 96]
    yield "classical", example
    for thermostat in ("quantum", "nozero"):
        for equilibrated in (True, False):
            case = copy.deepcopy(example)
            case.update(thermostat=thermostat, shape=[2, 3, 2], nfft=129, steps=120,
                        dt=0.003, decimation=7, sample_steps=[0, 1, 7, 31, 99, 120],
                        initial_memory="equilibrated" if equilibrated else "empty")
            case["materials"] = [
                dict(mu=0.4, K=-0.7, A=2450.0, omega0=35.0, Gamma=3.0, T=0.02,
                     initial_direction=[0.6, 0.1, 1.0]),
                dict(mu=2.8, K=0.3, A=144000.0, omega0=120.0, Gamma=60.0, T=0.3,
                     initial_direction=[-0.8, -0.3, -0.5]),
            ]
            case["exchange"] = [[0.8, -3.0], [-3.0, 0.4]]
            yield thermostat+"_"+case["initial_memory"], case
    for thermostat in ("classical", "quantum", "nozero"):
        case = copy.deepcopy(example)
        case.update(thermostat=thermostat, initial_memory="empty")
        case["materials"][0]["T"] = 0
        yield thermostat+"_zero", case
    case = copy.deepcopy(example)
    case.update(shape=[1, 1, 1], steps=0, sample_steps=[0, 0], nfft=33)
    yield "zero_duration", case
    case = copy.deepcopy(example)
    case.update(shape=[2, 2, 2], steps=60, dt=0.01, decimation=5, sample_steps=[0, 1, 5, 37, 60])
    case["materials"][0].update(omega0=500, Gamma=2000, A=2e6, T=3)
    yield "stiff_overdamped", case
    case = copy.deepcopy(example)
    case.update(shape=[2, 2, 2], nfft=8, steps=31, dt=0.01, decimation=4, sample_steps=[0, 13, 31])
    yield "periodic_endpoint", case
    case = copy.deepcopy(example)
    case.update(shape=[2, 2, 2], thermostat="quantum")
    case["materials"][0].update(A=1e-5)
    yield "weak_coupling", case


def check_noise():
    with open(PUBLIC) as source:
        case = json.load(source)
    case.update(shape=[4, 4, 12], nfft=8192, steps=51)
    spins, material, neighbors, parameters = solve.initialize(case)
    multipliers, covariance = solve.bath_spectrum(case)
    expected, expected_covariance = independent_noise(case, material)
    np.testing.assert_allclose(covariance, expected_covariance, rtol=2e-13, atol=2e-13)
    with tempfile.TemporaryDirectory(dir=ROOT) as scratch:
        for limit in (320*1024**2, 0):
            record = solve.NoiseRecord(case, material, multipliers, scratch, limit)
            for knot in range(record.length):
                np.testing.assert_allclose(record.knot(knot), expected[:, :, knot], rtol=2e-12, atol=2e-12)
            record.close()
    print("PASS batched Gaussian order, FFT filtering, and disk-backed noise", flush=True)


def check_analytic():
    with open(PUBLIC) as source:
        case = json.load(source)
    case.update(shape=[1, 1, 1], disorder=0, twist=0, field=[0, 0, 2], exchange=[[0]],
                steps=1000, dt=0.01, decimation=10, nfft=128, sample_steps=[0, 137, 1000])
    case["materials"][0].update(mu=2.3, K=0, A=0, T=0)
    initial = solve.initialize(case)[0][0]
    actual = solve.solve(case, ROOT)
    times = np.asarray(case["sample_steps"])*case["dt"]
    expected = np.stack((initial[0]*np.cos(2*times)+initial[1]*np.sin(2*times),
                         initial[1]*np.cos(2*times)-initial[0]*np.sin(2*times),
                         np.full_like(times, initial[2])), axis=-1)
    np.testing.assert_allclose(actual["trace"][:, 0], expected, rtol=0, atol=2e-9)
    np.testing.assert_array_equal(actual["memory"], 0)
    case.update(steps=130, nfft=32, sample_steps=[0, 17, 130], field=[0, 0, 0], initial_memory="empty")
    for gamma in (3, 14, 20):
        omega = 7
        case["materials"][0].update(A=98, omega0=omega, Gamma=gamma)
        duration = case["dt"]*case["steps"]
        if gamma < 2*omega:
            damped = np.sqrt(omega**2-gamma**2/4)
            exponential = np.exp(-gamma*duration/2)
            displacement = 2*(1-exponential*(np.cos(damped*duration)+gamma/(2*damped)*np.sin(damped*duration)))
            velocity = 2*exponential*omega**2/damped*np.sin(damped*duration)
        elif gamma == 2*omega:
            displacement = 2*(1-np.exp(-omega*duration)*(1+omega*duration))
            velocity = 2*omega**2*duration*np.exp(-omega*duration)
        else:
            split = np.sqrt(gamma**2/4-omega**2)
            slower, faster = -gamma/2+split, -gamma/2-split
            displacement = 2*(1+(faster*np.exp(slower*duration)-slower*np.exp(faster*duration))/(slower-faster))
            velocity = 2*omega**2*(np.exp(slower*duration)-np.exp(faster*duration))/(slower-faster)
        actual = solve.solve(case, ROOT)
        np.testing.assert_allclose(actual["spins"][0], initial, rtol=0, atol=2e-12)
        np.testing.assert_allclose(actual["memory"][0], np.concatenate((displacement*initial, velocity*initial)), rtol=0, atol=2e-8)
    print("PASS analytic precession and under/critical/overdamped oscillator restart states", flush=True)


def main():
    check_noise()
    check_analytic()
    for name, case in variants():
        started = time.perf_counter()
        actual = solve.solve(case, ROOT)
        expected = reference(case)
        errors = {}
        for key in actual:
            scale = max(1, float(np.max(np.abs(expected[key]))))
            errors[key] = float(np.max(np.abs(actual[key]-expected[key])))/scale
            tolerance = 2e-12 if key == "covariance" else 3e-7
            assert errors[key] < tolerance, (name, key, errors[key])
        np.testing.assert_allclose(np.linalg.norm(actual["spins"], axis=1), 1, rtol=0, atol=4e-16)
        print("PASS", name, errors, "seconds", round(time.perf_counter()-started, 3), flush=True)


if __name__ == "__main__":
    main()
