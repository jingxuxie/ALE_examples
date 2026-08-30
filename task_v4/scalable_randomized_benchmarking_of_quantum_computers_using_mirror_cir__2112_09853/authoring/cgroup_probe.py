import json
import os
from pathlib import Path
import subprocess
import time
import uuid


def main():
    record = Path('/proc/self/cgroup').read_text().strip()
    relative = next(line.split(':', 2)[2] for line in record.splitlines() if line.startswith('0::'))
    parent = Path('/sys/fs/cgroup') / relative.lstrip('/')
    group = parent / ('ale-mrb-probe-' + uuid.uuid4().hex)
    group.mkdir()
    result = {'parent': str(parent), 'group': str(group), 'parent_writable': os.access(parent / 'cgroup.procs', os.W_OK)}

    def join_group():
        (group / 'cgroup.procs').write_text(str(os.getpid()))

    try:
        result['before'] = (group / 'cpu.stat').read_text()
        program = 'import time\nstarted = time.process_time()\nwhile time.process_time() - started < 0.5:\n sum(range(1000))\n'
        subprocess.run(['/usr/bin/python3', '-c', program], preexec_fn=join_group, check=True, timeout=10)
        result['after'] = (group / 'cpu.stat').read_text()
        result['processes_after'] = (group / 'cgroup.procs').read_text()
    finally:
        if (group / 'cgroup.procs').read_text().strip():
            (group / 'cgroup.kill').write_text('1')
        for unused in range(100):
            if not (group / 'cgroup.procs').read_text().strip():
                break
            time.sleep(0.01)
        group.rmdir()
    result['cleaned'] = not group.exists()
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
