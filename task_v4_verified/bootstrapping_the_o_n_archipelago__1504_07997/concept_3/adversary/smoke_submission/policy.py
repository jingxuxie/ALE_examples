"""Trusted baseline smoke check from outside the participant directory."""

import os

import radial_public
from baseline_impl import main

assert "RADIAL_INPUT" not in os.environ
secret = radial_public.INPUT_DIR.parents[1] / "evaluator" / "hidden" / "seeds.json"
try:
    secret.read_text()
except PermissionError:
    pass
else:
    raise RuntimeError("hidden evaluator files are readable")

main()
