import json
from pathlib import Path
import subprocess


PILOT = Path(__file__).resolve().parents[2]


def store_text(relative, text):
    destination = PILOT / relative
    if not destination.is_relative_to(PILOT):
        raise ValueError('Outside pilot write scope')
    patch = '*** Begin Patch\n'
    if destination.exists():
        patch += '*** Update File: ' + str(destination) + '\n@@\n'
        patch += ''.join('-' + line + '\n' for line in destination.read_text().splitlines())
    else:
        patch += '*** Add File: ' + str(destination) + '\n'
    patch += ''.join('+' + line + '\n' for line in text.splitlines())
    patch += '*** End Patch\n'
    subprocess.run(['apply_patch'], input=patch, text=True, check=True, stdout=subprocess.DEVNULL)


def store_json(relative, payload):
    store_text(relative, json.dumps(payload, indent=2, allow_nan=False) + '\n')
