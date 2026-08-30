import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
from joint_solver import Joint, SOURCE
import improve
from polish import minimax
from collect import collect
os.environ['RESULT_DIR'] = 'final_results'

report = collect()
if not report['passed']:
    instance = json.loads(SOURCE.read_text())['instances'][0]
    solver = Joint(instance)
    minimax(solver)
    if solver.optimizer.best_error > 1e-8:
        from iht_refine import refine
        refine(solver, 60)
        solver.optimizer.improve(improve.load_seed(instance['id']), 30)
        minimax(solver)
collect()
