import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / 'participant' / 'workspace'))
from model import Episode
from transport import launch_command, run_episode

mode = sys.argv[1] if len(sys.argv) > 1 else 'bwrap'
submission = ROOT / 'submission'
command = launch_command(submission, 'policy.py', mode)
episode = Episode(349895, 'spam_drift', (5, 5))
result = run_episode(episode, command, ROOT, ROOT / ('validation_' + mode + '.stderr'),
                     transcript_path=ROOT / ('validation_' + mode + '.jsonl'))
print(json.dumps(result, indent=2))
