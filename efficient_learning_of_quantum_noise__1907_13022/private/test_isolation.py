import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from evaluation_sandbox import restrict_solver


ROOT = Path(__file__).resolve().parent


def main():
    secret = ROOT / 'CANDIDATES.md'
    alias = str(secret)[4:] if str(secret).startswith('/srv/home/') else '/srv' + str(secret)
    assert secret.exists() and Path(alias).exists()
    with tempfile.TemporaryDirectory(prefix='noise-isolation-') as directory:
        work = Path(directory)
        code = ('import pathlib,numpy,scipy,json; '
                'denied=[]; '
                f'paths={json.dumps([str(secret),alias])}; '
                '\nfor path in paths:\n'
                ' try:\n  pathlib.Path(path).read_bytes()\n  denied.append(False)\n'
                ' except PermissionError:\n  denied.append(True)\n'
                'pathlib.Path("output.txt").write_text("allowed"); '
                'print(json.dumps({"denied":denied,"numpy":numpy.__version__,"scipy":scipy.__version__})); '
                'assert all(denied)')
        env = dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        result = subprocess.run([sys.executable,'-c',code],cwd=work,env=env,text=True,capture_output=True,
                                preexec_fn=lambda: restrict_solver(work,work),timeout=15)
        report = dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,
                      writable_output=(work/'output.txt').exists())
        (ROOT/'isolation_audit.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
        assert result.returncode == 0, report


if __name__ == '__main__':
    main()
