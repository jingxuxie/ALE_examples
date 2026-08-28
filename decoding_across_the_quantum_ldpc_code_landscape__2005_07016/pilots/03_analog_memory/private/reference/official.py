from __future__ import annotations

import importlib
import sys
import time
import types

from runtime import SOURCE

import numpy as np
from ldpc import BpOsdDecoder
from scipy.special import ndtr


def modules():
    for name, relative in (
        ("mqt", "src/mqt"),
        ("mqt.qecc", "src/mqt/qecc"),
        ("mqt.qecc.analog_information_decoding", "src/mqt/qecc/analog_information_decoding"),
    ):
        if name not in sys.modules:
            package = types.ModuleType(name)
            package.__path__ = [str(SOURCE / relative)]
            sys.modules[name] = package
    return importlib.import_module(
        "mqt.qecc.analog_information_decoding.simulators.memory_experiment_v2"
    )


class RecordingDecoder:
    def __init__(self, decoder, free_columns, full_checks):
        self.decoder = decoder
        self.free_columns = free_columns
        self.full_checks = full_checks
        self.full_decoding = None

    def update_channel_probs(self, probabilities):
        self.decoder.update_channel_probs(probabilities[self.free_columns])

    def decode(self, syndrome):
        decoded = np.asarray(self.decoder.decode(syndrome), dtype=np.uint8)
        self.full_decoding = np.zeros(self.full_checks.shape[1], dtype=np.uint8)
        self.full_decoding[self.free_columns] = decoded
        if not np.array_equal(self.full_checks @ self.full_decoding % 2, syndrome):
            raise RuntimeError("Official decoder returned a vector outside the syndrome coset")
        return self.full_decoding

    @property
    def iter(self):
        return self.decoder.iter


def decoder_for(checks, priors, strong=True):
    return BpOsdDecoder(
        checks,
        channel_probs=priors,
        max_iter=80 if strong else 40,
        bp_method="minimum_sum",
        ms_scaling_factor=0.75,
        schedule="serial",
        osd_method="osd_cs" if strong else "osd_0",
        osd_order=6 if strong else 0,
        omp_thread_count=1,
    )


def decode_case(case, mode="reference"):
    started = time.process_time()
    checks = case["checks"]
    shots, rounds, num_checks = case["readout"].shape
    num_qubits = checks.shape[1]
    increments = np.zeros((shots, rounds, num_qubits), dtype=np.uint8)
    if mode == "weak":
        accumulated = (1 - np.prod(1 - 2 * case["data_error_prob"], axis=0)) / 2
        decoder = decoder_for(checks, accumulated, strong=False)
        for shot in range(shots):
            increments[shot, -1] = decoder.decode(case["terminal_syndrome"][shot])
    else:
        memory = modules()
        total_rounds = rounds + 1
        multiround = memory.build_multiround_pcm(checks, repetitions=rounds)
        block_size = total_rounds * num_qubits
        midpoints = (case["mean0"] + case["mean1"]) / 2
        separation = case["mean0"] - case["mean1"]
        transformed = (
            (case["readout"] - midpoints) * separation / (2 * case["sigma"] ** 2)
        )
        hard_syndromes = (transformed < 0).astype(np.uint8)
        hard_probability = ndtr(-np.abs(separation) / (2 * case["sigma"]))
        priors = np.concatenate((
            case["data_error_prob"].ravel(),
            np.full(num_qubits, 1e-15),
            hard_probability.ravel(),
            np.full(num_checks, 1e-15),
        ))
        free_columns = np.concatenate((
            np.arange(rounds * num_qubits),
            np.arange(block_size, block_size + rounds * num_checks),
        ))
        decoder = RecordingDecoder(
            decoder_for(multiround[:, free_columns], priors[free_columns]), free_columns, multiround
        )
        for shot in range(shots):
            syndromes = np.vstack((hard_syndromes[shot], case["terminal_syndrome"][shot])).T
            analog = np.vstack((
                np.clip(transformed[shot], -30, 30),
                30 * (1 - 2 * case["terminal_syndrome"][shot].astype(float)),
            )).T
            memory.decode_multiround(
                syndrome=syndromes.copy(),
                pcm=checks,
                decoder=decoder,
                channel_probs=priors,
                repetitions=total_rounds,
                analog_syndr=analog if mode == "reference" else None,
                last_round=True,
                check_block_size=block_size,
                sigma=1.0,
            )
            decoded = decoder.full_decoding
            if np.any(decoded[rounds * num_qubits : block_size]):
                raise RuntimeError("Reference assigned a fault to the ideal terminal interval")
            if np.any(decoded[-num_checks:]):
                raise RuntimeError("Reference altered the ideal terminal measurement")
            increments[shot] = decoded[: rounds * num_qubits].reshape(rounds, num_qubits)
    history = np.cumsum(increments, axis=1, dtype=np.int32) % 2
    syndrome_history = (history @ checks.T % 2).astype(np.uint8)
    return {
        "increments": increments,
        "syndrome_history": syndrome_history,
    }, time.process_time() - started
