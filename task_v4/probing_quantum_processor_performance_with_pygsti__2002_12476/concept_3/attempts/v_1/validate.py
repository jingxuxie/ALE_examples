import time

import numpy as np
from scipy.spatial.transform import Rotation

from model import CENTER, SCALE, load, predict, select


def reference(params, data):
    gates_ideal = [np.eye(3)] + [Rotation.from_rotvec(vector).as_matrix() for vector in
                    [[np.pi/2, 0, 0], [-np.pi/2, 0, 0], [0, np.pi/2, 0], [0, -np.pi/2, 0]]]
    pulse = np.array([[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]])
    results = []
    for row in range(len(data['length'])):
        acquisition = data['time'][row]
        sine_time = np.sin(2*np.pi*acquisition)
        reset = params[41:44] @ [1, 2*acquisition-1, sine_time]
        weight_one = 1/(1+np.exp(-reset))
        weights = np.array([1-weight_one, weight_one])
        prep = np.zeros(3)
        code = data['preparation'][row]
        prep[code//2] = 0.985 * (-1 if code % 2 else 1)
        bloch = weights[:, None]*prep
        memory = np.zeros(2)
        drift = params[26:29]*np.sin(2*np.pi*params[32]*acquisition) + params[29:32]*np.cos(2*np.pi*params[32]*acquisition)
        for gate in data['gates'][row, :data['length'][row]]:
            errors = params[:15].reshape(5, 3)[gate] + np.array([-1, 1])[:, None]*params[15:18]
            errors += params[18:24].reshape(3, 2) @ memory + drift
            for branch in range(2):
                bloch[branch] = Rotation.from_rotvec(errors[branch]).as_matrix() @ gates_ideal[gate] @ bloch[branch]
                bloch[branch, :2] *= np.sqrt(1-params[44+gate])
                bloch[branch, 2] = (1-params[44+gate])*bloch[branch, 2] + params[44+gate]*weights[branch]
                bloch[branch] *= 1-params[49+gate]
            logits = params[33:41].reshape(2, 4) @ [1, gate != 0, memory[0]-memory[1], sine_time]
            prob01, prob10 = 1/(1+np.exp(-logits))
            transition = np.array([[1-prob01, prob01], [prob10, 1-prob10]])
            weights = weights @ transition
            bloch = transition.T @ bloch
            memory = params[24:26]*memory + (1-params[24:26])*pulse[gate]
        results.append(0.008+0.979*(1-bloch[:, data['measurement'][row]].sum())/2)
    return np.array(results)


if __name__ == '__main__':
    rng = np.random.default_rng(1981)
    all_data = load('train')
    data = select(all_data, rng.choice(len(all_data['length']), 80, replace=False))
    params = CENTER + SCALE*rng.uniform(-0.8, 0.8, 54)
    output, jacobian = predict(params, data, True)
    independent = reference(params, data)
    print('reference error', np.max(np.abs(output-independent)), flush=True)
    assert np.max(np.abs(output-independent)) < 1e-10
    errors = []
    for component in range(54):
        delta = np.zeros(54)
        delta[component] = SCALE[component]*1e-5
        numeric = (predict(params+delta, data)-predict(params-delta, data))/(2e-5)
        analytic = jacobian[:, component]*SCALE[component]
        errors.append(np.max(np.abs(numeric-analytic)))
    print('scaled gradient max errors', errors, flush=True)
    assert max(errors) < 1e-7
    data = select(all_data, all_data['device'] == 0)
    started = time.monotonic()
    for repeat in range(5):
        predict(params, data, True)
    print('seconds per full device evaluation', (time.monotonic()-started)/5, flush=True)
