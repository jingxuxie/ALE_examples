import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
concept = ROOT / 'concept_01'
version = sys.argv[1] if len(sys.argv) > 1 else 'v_01'
participant = concept / 'participant' / version
attempt = concept / 'attempts' / version
screening = concept / 'screening' / version
launcher = ROOT.parents[1] / 'run_allowlisted_codex.sh'
prompt = f'''You are a fresh participant research agent. Read TASK.md in your current directory and complete its professional scientific task. You have up to one hour. Use only the participant directory {participant} and the writable attempt directory {attempt}. Do not inspect any other project, sibling directory, reference, evaluator, paper, previous session or network source. System Python and installed scientific libraries are available. Copy the starter modules into {attempt}/output/workspace before editing; preserve the participant input. Place your complete final deliverables at {attempt}/output. All scratch files must be under {attempt}. Work autonomously: run the baseline, investigate, repair, iterate, perform the required experiments, and deliver the executable system and evidence. The entry point and physical measurement contract are in TASK.md and input/CONTRACT.md. Do not stop after merely proposing a plan; execute it. Do not ask the user to do any steps.'''
command = [str(launcher), '--model', 'ultima-alpha', '--effort', 'high', str(participant), str(attempt), prompt]
fingerprints = {str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest() for path in participant.rglob('*') if path.is_file() and '__pycache__' not in path.parts and '.pytest_cache' not in path.parts}
(screening / 'participant_hashes_before.json').write_text(json.dumps(fingerprints, indent=2))
(screening / 'launch.json').write_text(json.dumps(dict(model='ultima-alpha', effort='high', time_limit_seconds=3600, participant=str(participant), writable_attempt=str(attempt), command=command, new_session=True, resumes_session=False), indent=2))
started = time.time()
with open(screening / 'transcript.log', 'w') as transcript:
    process = subprocess.Popen(['timeout', '--signal=TERM', '--kill-after=20', '3600'] + command, stdin=subprocess.DEVNULL, stdout=transcript, stderr=subprocess.STDOUT, cwd=participant, start_new_session=True)
    (screening / 'process.json').write_text(json.dumps(dict(pid=process.pid, started_unix=started)))
    returncode = process.wait()
elapsed = time.time() - started
after = {str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest() for path in participant.rglob('*') if path.is_file() and '__pycache__' not in path.parts and '.pytest_cache' not in path.parts}
result = dict(model='ultima-alpha', effort='high', runtime_seconds=elapsed, started_unix=started, finished_unix=time.time(), returncode=returncode, timed_out=returncode in [124, 137], participant_unchanged=fingerprints == after, transcript=str(screening / 'transcript.log'))
(screening / 'runtime.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2), flush=True)
