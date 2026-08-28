import json
from pathlib import Path
import tempfile
from isolated import run_submission

ROOT = Path(__file__).resolve().parents[1]
case = ROOT / 'pilots' / 'quantum_bath' / 'private' / 'challenge_pool' / 'initial_resonant_quantum_2317.json'
with tempfile.TemporaryDirectory(prefix='spin-scale-audit-') as directory:
    output = Path(directory) / 'output.json'
    result = run_submission(ROOT / 'authoring' / 'dense_noise_probe', case, output,
        ROOT / 'pilots' / 'quantum_bath' / 'participant', timeout=120)
    result['scope'] = 'Naive whole-record FFT allocation only; not a claim that all FFT-based methods fail.'
    result['atoms'] = 46656
    result['memory_limit_gib'] = 1.5
    if output.exists():
        result['output'] = json.load(open(output))
    (ROOT / 'authoring' / 'scale_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
