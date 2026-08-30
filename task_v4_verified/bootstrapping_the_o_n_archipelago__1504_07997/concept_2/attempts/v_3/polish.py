import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import time
import signal
import contextlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from scipy.optimize import least_squares
from joint_solver import Joint, ROOT, SOURCE
import improve
import continuous
os.environ['RESULT_DIR'] = 'polish_results'

class StageTimeout(BaseException):
    pass

def expired(*args):
    raise StageTimeout()

def minimax(solver):
    saved = improve.load_seed(solver.instance['id'])
    support = np.array([atom['index'] for atom in saved['atoms']])
    vectors = np.array([atom['ope'] for atom in saved['atoms']])
    solver.optimizer.evaluate(support, vectors)
    if solver.optimizer.best_error < 1e-8:
        return
    matrix = solver.design[:, support]
    weights = np.ones_like(solver.scales)
    def unpack(parameters):
        return np.r_[solver.optimizer.shared, parameters].reshape(-1, 2)
    def residual(parameters):
        return (((matrix @ improve.products(unpack(parameters))-solver.target)/solver.scales)*weights).ravel()
    def jacobian(parameters):
        current = unpack(parameters)
        jac = np.zeros((matrix.shape[0], 3, len(support), 2))
        jac[:, 0, :, 0] = 2*matrix*current[:, 0]
        jac[:, 1, :, 0] = matrix*current[:, 1]
        jac[:, 1, :, 1] = matrix*current[:, 0]
        jac[:, 2, :, 1] = 2*matrix*current[:, 1]
        return (jac*(weights/solver.scales)[:, :, None, None]).reshape(matrix.shape[0]*3, -1)[:, 1:]
    for iteration in range(15):
        solution = least_squares(residual, vectors.ravel()[1:], jac=jacobian, method='lm', max_nfev=3000, ftol=1e-14, xtol=1e-14, gtol=1e-14)
        vectors = unpack(solution.x)
        error = solver.optimizer.evaluate(support, vectors)
        print('MINIMAX', iteration, error, flush=True)
        if solver.optimizer.best_error < 1e-8:
            return
        raw = np.abs((matrix @ improve.products(vectors)-solver.target)/solver.scales)
        weights = np.sqrt(weights*np.maximum(raw/max(error, 1e-16), 0.01))
        weights /= np.max(weights)

def recover(index):
    instance = json.loads(SOURCE.read_text())['instances'][index]
    with (ROOT / ('polish_' + str(index) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            signal.signal(signal.SIGALRM, expired)
            solver = Joint(instance)
            if solver.optimizer.best_error < 1e-8:
                return solver.optimizer.best_error
            minimax(solver)
            for cycle in range(3):
                saved = improve.load_seed(instance['id'])
                solver.optimizer.evaluate([atom['index'] for atom in saved['atoms']], np.array([atom['ope'] for atom in saved['atoms']]))
                if solver.optimizer.best_error < 1e-8:
                    break
                for stage in ('continuous', 'discrete'):
                    signal.setitimer(signal.ITIMER_REAL, 100)
                    try:
                        if stage == 'continuous':
                            continuous.recover(instance, 95)
                        else:
                            improve.Optimizer(instance).improve(improve.load_seed(instance['id']), 95)
                    except StageTimeout:
                        print('TIMEOUT', stage, flush=True)
                    finally:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                minimax(solver)
            return solver.optimizer.best_error

if __name__ == '__main__':
    selected = list(map(int, sys.argv[1:])) or [0, 4, 5]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(recover, index): index for index in selected}
        for job in as_completed(jobs):
            print('POLISH_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
