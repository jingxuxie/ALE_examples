import json
from pathlib import Path
import tempfile
from isolated import run_submission

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='spin-isolation-audit-') as directory:
    directory = Path(directory)
    case = directory / 'case.json'
    case.write_text(json.dumps(dict(forbidden=[str(ROOT / 'authoring' / 'vampire'),
        str(ROOT / 'pilots' / 'quantum_bath' / 'private' / 'reference'),
        '/home/xuandong/.codex/auth.json', '/srv/home/xuandong/.codex/auth.json'])))
    output = directory / 'result.json'
    execution = run_submission(ROOT / 'authoring' / 'isolation_probe', case, output,
        ROOT / 'pilots' / 'quantum_bath' / 'participant', timeout=60)
    report = dict(execution=execution)
    if output.exists():
        report['observations'] = json.load(open(output))
    (ROOT / 'authoring' / 'isolation_audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    assert execution['returncode'] == 0
    assert not any(report['observations']['forbidden_visible'].values())
    assert not report['observations']['credentials_visible']
    assert not report['observations']['network_connected']
