import json
from pathlib import Path


root = Path(__file__).resolve().parent
circuits = [json.loads((root / filename).read_text())
            for filename in ('ladder_a.json', 'grid_a.json', 'bridge_a.json')]
artifact = {'schema_version': 1, 'circuits': circuits}
(root / 'artifact.json').write_text(json.dumps(artifact, indent=2) + '\n')
