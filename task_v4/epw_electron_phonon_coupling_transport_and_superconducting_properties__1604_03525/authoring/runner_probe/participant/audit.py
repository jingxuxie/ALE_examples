import json
from pathlib import Path
import socket
import sys
import numpy
import scipy


root = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/epw_electron_phonon_coupling_transport_and_superconducting_properties__1604_03525/authoring/runner_probe')
report = {'numpy_ok': True, 'scipy_ok': True, 'participant_readable': Path('TASK.md').is_file()}
try:
    content = (root / 'private_canary.txt').read_bytes()
    report.update(canonical_private_denied=False, unexpected_read_size=len(content))
except OSError as error:
    report.update(canonical_private_denied=True, exception_type=type(error).__name__, errno=error.errno)
try:
    connection = socket.create_connection(('1.1.1.1', 443), timeout=1)
    connection.close()
    report['network_denied'] = False
except OSError as error:
    report.update(network_denied=True, network_exception=type(error).__name__, network_errno=error.errno)
report['output_writable'] = True
Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
