import argparse
import json
import sys

import numpy as np

sys.path.insert(0, "/participant/input")
from model import Model


def send(message):
    print(json.dumps(message, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", choices=("adaptive", "minimax", "robust", "static", "uniform"), default="static")
    arguments = parser.parse_args()
    spec = json.loads(sys.stdin.readline())["spec"]
    model = Model(spec)
    action_count = len(spec["actions"])
    channel_count = len(spec["channels"])
    counts = np.zeros((action_count, model.state_count), dtype=np.int64)
    allocations = np.zeros(action_count)
    remaining = spec["shot_budget"]
    fitted = model.bounds.mean(axis=1)
    family_counts = {family: sum(channel["family"] == family for channel in spec["channels"])
                     for family in {channel["family"] for channel in spec["channels"]}}
    loss_weights = np.array([1.0 / family_counts[channel["family"]] for channel in spec["channels"]])

    def query(action_id, shots):
        nonlocal remaining
        send({"type": "query", "action": int(action_id), "shots": int(shots)})
        response = json.loads(sys.stdin.readline())
        counts[action_id] += response["counts"]
        allocations[action_id] += shots
        remaining -= shots

    for action_id in range(action_count):
        query(action_id, 160 if arguments.policy in ("minimax", "robust") else 100)
    fisher = model.fisher(fitted)
    rounds = 0
    while remaining:
        fit_frequency = 5 if arguments.policy == "adaptive" else 4
        if arguments.policy in ("adaptive", "minimax", "robust") and rounds % fit_frequency == 0:
            fitted = model.fit(counts, fitted, iterations=90)
            fisher = model.fisher(fitted)
            if arguments.policy == "robust":
                fisher = 0.7 * fisher + 0.3 * model.fisher(0.7 * fitted + 0.3 * model.bounds.mean(axis=1))
        shots = min(1200, remaining)
        if arguments.policy == "uniform":
            selected = int(np.argmin(allocations))
        else:
            information = np.einsum("a,akl->kl", allocations, fisher) + np.eye(channel_count) * 0.5
            projected = np.linalg.inv(information[None, :, :] + shots * fisher)
            risks = np.einsum("akk,k->a", projected, loss_weights)
            if arguments.policy in ("minimax", "robust"):
                diagonal = np.diagonal(projected, axis1=1, axis2=2)
                family_risks = np.stack([np.sqrt(np.mean(diagonal[:, [index for index, channel in enumerate(spec["channels"])
                                                                              if channel["family"] == family]], axis=1))
                                         for family in sorted(family_counts)], axis=1)
                risks = 0.5 * np.mean(family_risks, axis=1) + 0.5 * np.max(family_risks, axis=1)
            selected = int(np.argmin(risks))
        query(selected, shots)
        rounds += 1
    fitted = model.fit(counts, fitted, iterations=180)
    send({"type": "final", "rates": np.exp(fitted).tolist()})


if __name__ == "__main__":
    main()
