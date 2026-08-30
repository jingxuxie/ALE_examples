import json
from pathlib import Path

SOURCE = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_3/participant')
target = json.loads((SOURCE / 'input/target.json').read_text())
Path('target.txt').write_text('\n'.join(target['x_outputs'] + target['z_outputs']) + '\n')
