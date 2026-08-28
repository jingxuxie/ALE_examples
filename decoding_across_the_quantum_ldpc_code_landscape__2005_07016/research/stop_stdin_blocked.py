import os
from pathlib import Path
import signal

root = str(Path(__file__).resolve().parents[1])
for process_path in Path('/proc').iterdir():
    if not process_path.name.isdigit():
        continue
    try:
        arguments = (process_path / 'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if not arguments or Path(os.fsdecode(arguments[0])).name != 'timeout':
        continue
    command = ' '.join(os.fsdecode(argument) for argument in arguments)
    if root not in command or 'run_allowlisted_codex.sh' not in command:
        continue
    process_id = int(process_path.name)
    print('Stopping only this task stdin-blocked launch group', process_id, flush=True)
    os.killpg(process_id, signal.SIGTERM)
