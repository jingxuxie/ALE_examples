import json
from pathlib import Path

import numpy as np
from scipy.interpolate import BSpline
from scipy.special import betainc


def build():
    times = np.linspace(0.0, 8.0, 501)
    fraction = np.clip((times - 2.2) / 5.8, 0.0, 1.0)
    desired = betainc(5, 5, fraction)
    acceleration = 2520.0 * fraction ** 3 * (1.0 - fraction) ** 3 * (1.0 - 2.0 * fraction) / 5.8 ** 2
    knots = np.r_[np.zeros(4), np.linspace(0.0, 8.0, 23)[1:-1], np.full(4, 8.0)]
    basis = BSpline(knots, np.eye(25), 3)(times)
    transport = np.zeros(25)
    transport[-3:] = 1.0
    transport[3:-3] = np.linalg.lstsq(basis[:, 3:-3], desired + acceleration - basis @ transport, rcond=None)[0]
    rf = np.zeros(25)
    rf[3:6] = [1.2, 1.8, 1.2]
    return {"schema_version": 1, "controls": {"center": transport.tolist(), "separation": (2.2 * transport).tolist(), "omega_x": rf.tolist(), "omega_y": np.zeros(25).tolist(), "detuning": np.zeros(25).tolist(), "curvature": np.ones(25).tolist()}}


if __name__ == "__main__":
    output = Path(__file__).with_name("control.json")
    output.write_text(json.dumps(build(), indent=2, allow_nan=False) + "\n")
    print(output)
