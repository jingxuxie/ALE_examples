"""Trusted, importable worker for bounded parallel circuit recomputation."""

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def load_module(name):
    module_name = "trusted_worker_" + name
    specification = importlib.util.spec_from_file_location(module_name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


ENGINE = load_module("simulator")
REFERENCE = load_module("reference")
PROTOCOL = load_module("protocol")
SPEC = json.loads((ROOT / "target.json").read_text())


def evaluate_waveform(job):
    family, angles = job
    truth = REFERENCE.zz1(REFERENCE.exact_state(angles))
    estimates, diagnostics = [], {}
    for chi in SPEC["chis"]:
        state, diagnostic = ENGINE.mps_state(angles, chi)
        estimates.append(REFERENCE.zz1(state))
        diagnostics[str(chi)] = diagnostic
    record = PROTOCOL.metrics(truth, estimates, SPEC)
    record["diagnostics"] = diagnostics
    return family, record
