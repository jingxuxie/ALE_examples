import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ["JAX_PLATFORMS"] = "cpu"
os.environ.setdefault("XLA_FLAGS", "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1")

import argparse
import json
import sys
import time
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

jax.config.update("jax_enable_x64", True)

SOURCE = Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/solving_statistical_mechanics_using_variational_autoregressive_network__1809_10606/concept_3/generations/generation_2/participant")
sys.path.insert(0, str(SOURCE))
from transfer import model_from_edges, spin_states


class Inference:
    def __init__(self, observations=None):
        self.spec = json.loads((SOURCE / "input/model.json").read_text())
        self.queries = json.loads((SOURCE / "input/queries.json").read_text())
        archive = np.load(SOURCE / "input/train.npz")
        self.betas = np.asarray(archive["betas"])
        self.observations = archive["visible_spins"] if observations is None else observations
        self.count = self.observations.shape[1]
        self.edges = np.asarray(self.spec["edges"])
        self.signs = np.asarray(self.spec["edge_signs"])
        self.visible = np.asarray(self.spec["visible_indices"])
        self.hidden = np.asarray(self.spec["hidden_indices"])
        self.edge_count = len(self.edges)
        self.dimension = self.edge_count + 96
        self.lower = np.r_[np.full(self.edge_count, 0.3), np.full(96, -0.12)]
        self.upper = np.r_[np.full(self.edge_count, 0.95), np.full(96, 0.12)]
        self.sign_all = np.r_[self.signs, np.ones(96)]
        self.states = jnp.asarray(spin_states(8), dtype=jnp.float64)
        self.products = self.states[:, :-1] * self.states[:, 1:]
        self.flips = jnp.asarray(np.arange(256)[None, :] ^ (1 << np.arange(8))[:, None])
        observed_full = np.zeros((2, self.count, 96))
        observed_full[:, :, self.visible] = self.observations
        visible_statistics = np.concatenate(
            [np.mean(observed_full[:, :, self.edges[:, 0]] * observed_full[:, :, self.edges[:, 1]], axis=1),
             np.mean(observed_full, axis=1)], axis=1)
        self.visible_linear = jnp.asarray((self.betas[:, None] * visible_statistics).sum(axis=0) * self.sign_all)
        remaining = set(self.hidden.tolist())
        components = []
        while remaining:
            component = {remaining.pop()}
            while True:
                additions = ({int(right) for left, right in self.edges if left in component and right in remaining}
                             | {int(left) for left, right in self.edges if right in component and left in remaining})
                if not additions:
                    break
                component |= additions
                remaining -= additions
            components.append(sorted(component))
        self.components = []
        for component in components:
            hidden_index = {site: index for index, site in enumerate(component)}
            neighbors = sorted(({int(right) for left, right in self.edges if left in component}
                                | {int(left) for left, right in self.edges if right in component}) - set(component))
            neighbor_index = {site: index for index, site in enumerate(neighbors)}
            hidden_states = spin_states(len(component)).astype(float)
            neighbor_states = spin_states(len(neighbors)).astype(float)
            local_features = []
            local_indices = []
            boundary_hidden = []
            boundary_visible = []
            boundary_indices = []
            for edge_index, (left, right) in enumerate(self.edges):
                if left in hidden_index and right in hidden_index:
                    local_features.append(hidden_states[:, hidden_index[left]] * hidden_states[:, hidden_index[right]])
                    local_indices.append(edge_index)
                elif left in hidden_index or right in hidden_index:
                    hidden_site, visible_site = (left, right) if left in hidden_index else (right, left)
                    boundary_hidden.append(hidden_index[hidden_site])
                    boundary_visible.append(neighbor_index[visible_site])
                    boundary_indices.append(edge_index)
            for site in component:
                local_features.append(hidden_states[:, hidden_index[site]])
                local_indices.append(self.edge_count + site)
            codes = ((observed_full[:, :, neighbors] + 1).astype(np.int64) // 2) @ (1 << np.arange(len(neighbors)))
            counts = np.stack([np.bincount(codes[condition], minlength=len(neighbor_states)) for condition in range(2)])
            used = np.flatnonzero(counts.sum(axis=0))
            self.components.append((
                jnp.asarray(np.asarray(local_features).T), jnp.asarray(local_indices),
                jnp.asarray(hidden_states[:, boundary_hidden].T),
                jnp.asarray(neighbor_states[used][:, boundary_visible]), jnp.asarray(boundary_indices),
                jnp.asarray(counts[:, used] / self.count),
            ))
        self.value_grad = jax.jit(jax.value_and_grad(self.loss))
        self.partition = jax.jit(self.log_partition)

    def hessian(self, theta, epsilon=1e-4):
        result = np.empty((self.dimension, self.dimension))
        for coordinate in range(self.dimension):
            displacement = np.zeros(self.dimension)
            displacement[coordinate] = epsilon
            result[:, coordinate] = (self.scipy_loss(theta + displacement)[1] - self.scipy_loss(theta - displacement)[1]) / (2 * epsilon)
        return (result + result.T) / 2

    def log_partition(self, theta, beta):
        signed = theta * jnp.asarray(self.sign_all)
        vertical = signed[:84].reshape(12, 7)
        horizontal = signed[84:172].reshape(11, 8)
        fields = signed[172:].reshape(12, 8)
        energies = beta * (vertical @ self.products.T + fields @ self.states.T)
        shifts = jnp.max(energies, axis=1)
        unary = jnp.exp(energies - shifts[:, None])
        first_norm = jnp.sum(unary[0])

        def column_step(carry, values):
            forward, lognorm = carry
            unary_column, coupling, shift = values

            def row_step(weights, row_values):
                strength, permutation = row_values
                return jnp.exp(beta * strength) * weights + jnp.exp(-beta * strength) * weights[permutation], None

            propagated, _ = jax.lax.scan(row_step, forward, (coupling, self.flips))
            weights = unary_column * propagated
            norm = jnp.sum(weights)
            return (weights / norm, lognorm + jnp.log(norm) + shift), None

        (_, result), _ = jax.lax.scan(column_step, (unary[0] / first_norm, jnp.log(first_norm) + shifts[0]),
                                     (unary[1:], horizontal, shifts[1:]))
        return result

    def loss(self, theta):
        signed = theta * jnp.asarray(self.sign_all)
        result = sum(self.log_partition(theta, beta) for beta in self.betas)
        result -= self.visible_linear @ theta
        for local_features, local_indices, boundary_hidden, boundary_visible, boundary_indices, weights in self.components:
            energies = local_features @ signed[local_indices]
            energies = energies[None, :] + (boundary_visible * signed[boundary_indices]) @ boundary_hidden
            for condition, beta in enumerate(self.betas):
                result -= weights[condition] @ jax.scipy.special.logsumexp(beta * energies, axis=1)
        return self.count * result

    def scipy_loss(self, theta):
        loss, gradient = self.value_grad(theta)
        return float(loss), np.asarray(gradient)

    def predict(self, theta):
        model = model_from_edges(self.spec, theta[:172] * self.signs, theta[172:])
        probabilities = []
        marginal_cache = {}
        for query in self.queries:
            beta = query["beta"]
            if beta not in marginal_cache:
                marginal_cache[beta] = model.column_marginals(beta)
            readout = np.asarray(query["readout"])
            codes = ((model.states[:, readout % 8] + 1) // 2) @ (1 << np.arange(6))
            marginal = marginal_cache[beta][readout[0] // 8]
            joint = np.bincount(codes, weights=marginal, minlength=64)
            fields = np.zeros(6)
            for site, field in zip(query["field_indices"], query["field_values"]):
                fields[list(readout).index(site)] = field
            logits = np.log(joint) + beta * (spin_states(6) @ fields)
            joint = np.exp(logits - logsumexp(logits))
            probabilities.append(joint)
        return np.asarray(probabilities)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=600)
    parser.add_argument("--start", type=str)
    parser.add_argument("--output", type=str, default="fit.npz")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()
    inference = Inference()
    rng = np.random.default_rng(args.seed)
    theta = np.r_[np.full(172, 0.625), np.zeros(96)]
    if args.start:
        theta = np.load(args.start)["theta"]
    started = time.time()
    loss, gradient = inference.scipy_loss(theta)
    print("compiled", time.time() - started, "loss", loss, "gradient", np.linalg.norm(gradient), flush=True)
    reference = model_from_edges(inference.spec, theta[:172] * inference.signs, theta[172:])
    for beta in [0.65, 1.0]:
        actual = float(inference.partition(theta, beta))
        expected = reference.log_partition(beta)
        np.testing.assert_allclose(actual, expected, atol=1e-10)
    direction = rng.normal(size=268)
    direction /= np.linalg.norm(direction)
    epsilon = 1e-5
    numeric = (inference.scipy_loss(theta + epsilon * direction)[0] - inference.scipy_loss(theta - epsilon * direction)[0]) / (2 * epsilon)
    np.testing.assert_allclose(numeric, gradient @ direction, rtol=1e-5, atol=1e-4)
    benchmark = time.time()
    for _ in range(20):
        inference.scipy_loss(theta)
    print("gradient seconds", (time.time() - benchmark) / 20, flush=True)
    steps = [0]

    def callback(current):
        steps[0] += 1
        if steps[0] % 25 == 0:
            loss, gradient = inference.scipy_loss(current)
            print("iteration", steps[0], "loss", loss, "gradient", np.linalg.norm(gradient), "elapsed", time.time() - started, flush=True)
            np.savez(args.output, theta=current, loss=loss)

    result = minimize(inference.scipy_loss, theta, method="L-BFGS-B", jac=True,
                      bounds=list(zip(inference.lower, inference.upper)), callback=callback,
                      options={"maxiter": args.iterations, "ftol": 1e-13, "gtol": 1e-5, "maxls": 30, "maxcor": 40})
    print(result.message, "loss", result.fun, "iterations", result.nit, "elapsed", time.time() - started, flush=True)
    np.savez(args.output, theta=result.x, loss=result.fun, gradient=result.jac, probabilities=inference.predict(result.x))
    print("calculating Hessian", flush=True)
    hessian = np.asarray(inference.hessian(result.x))
    np.save(args.output.replace(".npz", "_hessian.npy"), hessian)
    eigenvalues = np.linalg.eigvalsh(hessian)
    print("Hessian eigenvalues", eigenvalues[:12], eigenvalues[-5:], "elapsed", time.time() - started, flush=True)


if __name__ == "__main__":
    main()
