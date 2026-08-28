import argparse
import io
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
import numpy as np


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'private'))
from evaluation_sandbox import restrict_solver
KEYS = ['probabilities','correlations','conditional_information','spatial_jsd']


def load_output(path, target):
    descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as stream:
        status = os.fstat(stream.fileno())
        if not stat.S_ISREG(status.st_mode) or status.st_size > 16*1024**2:
            raise ValueError('output must be a bounded regular file')
        with zipfile.ZipFile(stream) as archive:
            names = [entry.filename for entry in archive.infolist()]
            if sorted(names) != sorted(key+'.npy' for key in KEYS):
                raise ValueError('incorrect output archive fields')
            result = {}
            for key in KEYS:
                expected_shape = np.asarray(target[key]).shape
                entry = archive.getinfo(key+'.npy')
                if entry.file_size > 65536+8*int(np.prod(expected_shape)):
                    raise ValueError('oversized output member')
                content = archive.read(key+'.npy')
                member = io.BytesIO(content)
                version = np.lib.format.read_magic(member)
                if version == (1,0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(member)
                elif version == (2,0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(member)
                else:
                    raise ValueError('unsupported array format')
                if shape != expected_shape or dtype.kind not in 'biuf' or dtype.itemsize > 8:
                    raise ValueError('incorrect output array shape or dtype')
                result[key] = np.load(io.BytesIO(content),allow_pickle=False)
            return result


def errors(predicted, reference):
    distribution = np.asarray(predicted['probabilities'])
    target = reference['probabilities']
    if distribution.shape != target.shape or np.any(distribution < -1e-8) or abs(distribution.sum()-1) > .01:
        raise ValueError('invalid probability distribution')
    values = []
    for key in KEYS:
        actual = np.asarray(predicted[key])
        expected = np.asarray(reference[key])
        if actual.shape != expected.shape or not np.all(np.isfinite(actual)):
            raise ValueError(f'invalid {key}')
        if key == 'probabilities':
            values.append(float(np.abs(actual[1:]-expected[1:]).sum()/max(1-expected[0],.01)))
        elif key == 'correlations':
            off_diagonal = ~np.eye(len(expected),dtype=bool)
            values.append(float(np.sqrt(np.mean((actual[off_diagonal]-expected[off_diagonal])**2))))
        else:
            values.append(float(np.sqrt(np.mean((actual-expected)**2))))
    return np.asarray(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission',required=True)
    parser.add_argument('--pool',choices=['core','challenge'],default='core')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    submission = Path(args.submission).resolve()
    manifest = json.loads((ROOT/'reference'/'manifest.json').read_text())
    records = []
    for item in manifest:
        if item['pool'] != args.pool:
            continue
        source = np.load(ROOT/item['input'])
        target = np.load(ROOT/item['reference'])
        baseline = dict(probabilities=source['counts'][0]/source['counts'][0].sum(),
                        correlations=np.eye(len(source['blocks'])),
                        conditional_information=np.zeros(len(source['conditional_queries'])),spatial_jsd=np.array(0.))
        weak_errors = errors(baseline,target)
        scale = .12*weak_errors + np.asarray([.001,.001,.00001,.0005])
        started = time.monotonic()
        record = dict(id=item['id'],family=item['family'])
        with tempfile.TemporaryDirectory(prefix='noise-eval-') as temporary:
            work = Path(temporary)
            shutil.copy2(submission, work/'solver.py')
            np.savez(work/'input.npz',**{key:source[key] for key in source.files})
            env = dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
                       TMPDIR=str(work),HOME=str(work),NUMBA_CACHE_DIR=str(work/'cache'))
            try:
                child = subprocess.run([sys.executable,str(work/'solver.py'),str(work/'input.npz'),str(work/'output.npz')],
                                       cwd=work,env=env,capture_output=True,text=True,timeout=120,
                                       preexec_fn=lambda: restrict_solver(work,work))
                if child.returncode:
                    raise RuntimeError(child.stderr[-2000:])
                predicted = load_output(work/'output.npz',target)
                loss = errors(predicted,target)
                component_scores = scale/(scale+loss)
                record.update(score=float(component_scores.mean()),components=dict(zip(KEYS,component_scores.tolist())),
                              losses=dict(zip(KEYS,loss.tolist())),weak_losses=dict(zip(KEYS,weak_errors.tolist())))
            except Exception as error:
                record.update(score=0.,error=str(error))
        record['seconds'] = time.monotonic()-started
        records.append(record)
    families = {family:float(np.mean([row['score'] for row in records if row['family']==family]))
                for family in sorted({row['family'] for row in records})}
    result = dict(mean_core=float(np.mean([row['score'] for row in records])),worst_family=min(families.values()),
                  families=families,cases=records,total_seconds=sum(row['seconds'] for row in records),pool=args.pool)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='cases'}))


if __name__ == '__main__':
    main()
