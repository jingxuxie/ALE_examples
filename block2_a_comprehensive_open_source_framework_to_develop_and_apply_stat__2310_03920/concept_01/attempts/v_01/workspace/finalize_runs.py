import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
for case in ['spin_orbit_scale_14', 'paired_scale_14', 'vibronic_scale_6_levels4', 'vibronic_scale_10_levels4']:
    final = ROOT / 'runs' / (case + '_final_policy')
    destination = ROOT / 'runs' / (case + '_production')
    if final.exists() and (final / 'stats.json').exists():
        if destination.exists():
            stats_path = destination / 'stats.json'
            bond = json.loads(stats_path.read_text())['settings'].get('bond') if stats_path.exists() else 160
            destination.rename(ROOT / 'runs' / (case + ('_pilot160' if bond == 160 else '_pilot')))
        final.rename(destination)
for case, suffix in [('vibronic_scale_6_levels3', 'final_tensor'), ('vibronic_scale_6_levels4', 'final_policy'),
                      ('vibronic_scale_10_levels4', 'final_policy')]:
    original = ROOT / 'runs' / (case + '_' + suffix + '_warmup')
    if original.exists():
        original.rename(ROOT / 'runs' / (case + '_warmup'))
for folder in ['runs', 'replays']:
    for directory in (ROOT / folder).iterdir():
        if (directory / 'stats.json').exists() or (directory / 'failure.json').exists():
            for name in ['scratch', 'tmp']:
                if (directory / name).exists():
                    shutil.rmtree(directory / name)
print('Canonicalized completed final runs and removed reconstructible scratch data.')
