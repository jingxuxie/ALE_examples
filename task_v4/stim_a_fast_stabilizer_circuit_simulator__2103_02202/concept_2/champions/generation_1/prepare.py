import json
from pathlib import Path

source = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2/participant/input/model.json')
model = json.loads(source.read_text())
with Path('columns.txt').open('w') as output:
    for column, observable in zip(model['columns'], model['observable']):
        value = int(column, 16)
        words = [(value >> offset) & ((1 << 64) - 1) for offset in (0, 64, 128)]
        output.write(' '.join(f'{word:016x}' for word in words) + f' {observable}\n')
