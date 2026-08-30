import json
import sys
import time
from pathlib import Path

root = Path('/tmp/cascade-c2-g2-v3-mirk7s27')
output = root / 'attempts/v_3'
sys.path.insert(0, str(root / 'participant/workspace'))
from replay import replay

deployment = json.loads((root / 'participant/input/deployment.json').read_text())
blocks = []
for specification in deployment['passes']:
    block_map = [0] * deployment['n']
    for offset, position in enumerate(specification['permutation']):
        block_map[position] = offset // specification['block_size']
    blocks.append(block_map)

def finalize(candidate):
    try:
        core = json.loads(candidate.read_text())['errors']
    except (ValueError, KeyError, OSError):
        return False
    if not 8 <= len(core) <= 18 or len(set(core)) != len(core):
        return False
    if any(type(position) is not int or not 0 <= position < 8192 for position in core):
        return False
    for block_map in blocks:
        syndrome = 0
        for position in core:
            syndrome ^= 1 << block_map[position]
        if syndrome:
            return False
    occupied = {blocks[0][position] for position in core}
    activation = []
    for position in deployment['passes'][0]['permutation']:
        block = blocks[0][position]
        if block not in occupied:
            activation.append(position)
            occupied.add(block)
            if len(activation) == 6:
                break
    errors = sorted(core + activation)
    results = [replay(deployment, errors, priority) for priority in ('earliest', 'shortest')]
    for result in results:
        assert result['initial_odd'] >= 6
        assert len(result['corrected']) >= 6
        assert len(result['residual']) >= 8
        assert result['residual'] == sorted(core)
    assert 1 <= len(errors) <= 24
    temporary = output / 'witness.tmp'
    temporary.write_text(json.dumps({'errors': errors}) + '\n')
    temporary.replace(output / 'witness.json')
    (output / 'validation.json').write_text(json.dumps({'source': candidate.name, 'core': sorted(core), 'activation': activation, 'replays': results}, indent=2) + '\n')
    print('VALIDATED', candidate.name, len(errors), results, flush=True)
    return True

while True:
    for candidate in sorted(output.glob('*core*.json')):
        if finalize(candidate):
            sys.exit(0)
    if '--watch' not in sys.argv:
        sys.exit(1)
    time.sleep(5)
