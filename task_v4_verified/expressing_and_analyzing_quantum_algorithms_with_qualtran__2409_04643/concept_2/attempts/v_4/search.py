import argparse
import json
import time
from pathlib import Path

import numpy as np


def completion(polynomials, fft_size=512):
    values = np.fft.ifft(polynomials, n=fft_size, axis=-1, norm="forward")
    fourier = np.fft.fft(np.log1p(-abs(values) ** 2), axis=-1, norm="forward")
    fourier[:, 0] *= 0.5
    fourier[:, fft_size // 2 + 1 :] = 0
    return np.fft.fft(np.exp(np.fft.ifft(fourier, axis=-1, norm="forward")), axis=-1, norm="forward")[:, :polynomials.shape[-1]]


def extract(polynomials, complements):
    count, length = polynomials.shape
    top = polynomials.copy()
    bottom = complements.copy()
    theta = np.zeros((count, length))
    phi = np.zeros_like(theta)
    margins = np.full(count, np.inf)
    leaders = np.zeros((count, length))
    for degree in reversed(range(length)):
        leading, other = top[:, degree], bottom[:, degree]
        theta[:, degree] = np.arctan2(abs(other), abs(leading))
        phi[:, degree] = np.angle(leading * other.conj())
        margins = np.minimum(margins, np.minimum(abs(other), abs(leading * other.conj())))
        leaders[:, degree] = np.sqrt(abs(leading) ** 2 + abs(other) ** 2)
        if degree:
            cosine = np.cos(theta[:, degree])[:, None]
            sine = np.sin(theta[:, degree])[:, None]
            phase = np.exp(-1j * phi[:, degree])[:, None]
            top, bottom = (cosine * phase * top + sine * bottom)[:, 1:], (sine * phase * top - cosine * bottom)[:, :-1]
    lambd = np.angle(bottom[:, 0])
    return theta, phi, lambd, margins, leaders


def reconstruct(theta, phi, lambd):
    top = (np.exp(1j * (phi[:, 0] + lambd)) * np.cos(theta[:, 0]))[:, None]
    bottom = (np.exp(1j * lambd) * np.sin(theta[:, 0]))[:, None]
    for degree in range(1, theta.shape[-1]):
        top = np.pad(top, ((0, 0), (1, 0)))
        bottom = np.pad(bottom, ((0, 0), (0, 1)))
        cosine = np.cos(theta[:, degree])[:, None]
        sine = np.sin(theta[:, degree])[:, None]
        phase = np.exp(1j * phi[:, degree])[:, None]
        top, bottom = phase * (cosine * top + sine * bottom), sine * top - cosine * bottom
    return top, bottom


def screen(polynomials, fft_size=512):
    complements = completion(polynomials, fft_size)
    theta, phi, lambd, margins, leaders = extract(polynomials, complements)
    actual_top, actual_bottom = reconstruct(theta, phi, lambd)
    overlap = np.sum(polynomials.conj() * actual_top + complements.conj() * actual_bottom, axis=-1)
    phase = (overlap / abs(overlap))[:, None]
    errors = np.sqrt(np.sum(abs(actual_top - phase * polynomials) ** 2 + abs(actual_bottom - phase * complements) ** 2, axis=-1))
    return errors, margins, leaders


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=100)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--degree", type=int, default=14)
    parser.add_argument("--seed", type=int, default=13456)
    parser.add_argument("--amplitude-spread", type=float, default=0)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    best = 0
    for batch in range(args.batches):
        polynomials = np.exp(1j * rng.uniform(-np.pi, np.pi, (args.size, args.degree + 1)))
        if args.amplitude_spread:
            polynomials *= np.exp(rng.normal(0, args.amplitude_spread, polynomials.shape))
        polynomials *= (0.78 / np.max(abs(np.fft.fft(polynomials, n=1024, axis=-1)), axis=-1))[:, None]
        energy = np.sum(abs(polynomials) ** 2, axis=-1)
        rms = np.sqrt(energy / polynomials.shape[-1])
        valid = (energy >= 0.08) & (energy <= 0.30) & (abs(np.sum(polynomials ** 2, axis=-1)) <= 0.8 * energy)
        valid &= np.min(abs(polynomials), axis=-1) >= 0.25 * rms
        valid &= np.max(abs(polynomials), axis=-1) <= 4 * rms
        errors, margins, leaders = screen(polynomials)
        errors[~valid | (margins < 1e-8)] = 0
        selected = np.argmax(errors)
        if errors[selected] > best:
            best = errors[selected]
            chosen = polynomials[selected]
            Path("search_best.json").write_text(json.dumps({"P": [[float(value.real), float(value.imag)] for value in chosen]}))
            print("BEST", batch, best, "margin", margins[selected], "leaders", leaders[selected], flush=True)
        if batch % 10 == 0:
            print("PROGRESS", batch, "elapsed", time.monotonic() - started, "quantiles", np.quantile(errors, [0.5, 0.9, 0.99, 1]), "minmargin", margins.min(), flush=True)


if __name__ == "__main__":
    main()
