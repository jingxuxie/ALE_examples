import itertools
import json
import math
import subprocess
import sys
import time

import numpy as np
from scipy.optimize import minimize

from refine import ComputeLimit, ExactModel, HERE, PassingMargin, ROOT, protected_hashes, save


def main():
    first = json.loads((HERE/'search_summary.json').read_text())
    consumed = first['optimization_cpu_seconds']
    budget = max(0.0,600.0-consumed-10.0)
    before = json.loads((HERE/'protected_before.json').read_text())
    assert protected_hashes()==before
    model = ExactModel()
    initial_payload = json.loads((HERE/'submission.json').read_text())
    starting_word = [stage['component'] for stage in initial_payload['stages'][:17]]
    starting_weights = np.array([stage['coefficient'] for stage in initial_payload['stages'][:17]])
    started_cpu,started_wall = time.process_time(),time.monotonic()
    history,optimizations,gradient_checks,scan = [],[],[],[]
    best = {'metrics':{'maximum_gate_ratio':float('inf')}}
    phase = 'balanced_fixed_word'
    last_progress = started_wall

    def guard():
        if time.process_time()-started_cpu>budget-2 or time.monotonic()-started_wall>budget-2:
            raise ComputeLimit()

    def set_word(word):
        model.word = list(word)
        model.groups = [np.array([index for index,label in enumerate(word) if label==component]) for component in model.labels]
        model.last_parameters,model.last_result = None,None

    def tracked(parameters, derivatives=True):
        nonlocal best,last_progress
        guard()
        if derivatives:
            squared,jacobian = model.get(parameters)
        else:
            squared,jacobian = model.evaluate(parameters,derivatives=False),None
        metrics = model.metrics(squared)
        if metrics['maximum_gate_ratio']<best['metrics']['maximum_gate_ratio']:
            best={'word':list(model.word),'parameters':parameters.copy(),'metrics':metrics}
            save('refined_submission.json',model.payload(parameters))
            save('refined_model_report.json',metrics)
            history.append({'phase':phase,'cpu_seconds_this_phase':time.process_time()-started_cpu,**metrics})
        if time.monotonic()-last_progress>15:
            print('PROGRESS',json.dumps({'phase':phase,'aggregate_optimization_cpu_seconds':consumed+time.process_time()-started_cpu,**best['metrics']}),flush=True)
            last_progress=time.monotonic()
        if metrics['maximum_gate_ratio']<=0.999:
            raise PassingMargin()
        return squared,jacobian

    def gates(squared,jacobian=None):
        ratios=np.sqrt(squared)
        family_squared=np.array([np.mean(squared[mask]) for mask in model.family_masks])
        family_gates=model.targets['worst_family_score_min']*np.sqrt(family_squared)
        core_gate=model.targets['core_score_min']*np.exp(0.5*np.mean(np.log(family_squared)))
        values=np.concatenate((ratios,family_gates,[core_gate]))
        if jacobian is None:
            return values,None
        family_jacobian=np.array([np.mean(jacobian[mask],axis=0) for mask in model.family_masks])
        derivative=np.concatenate((jacobian/(2*ratios[:,None]),model.targets['worst_family_score_min']*family_jacobian/(2*np.sqrt(family_squared)[:,None]),(0.5*core_gate*np.mean(family_jacobian/family_squared[:,None],axis=0))[None,:]),axis=0)
        return values,derivative

    def optimize(word,weights,maximum_iterations):
        set_word(word)
        parameters=model.encode(weights)
        squared,jacobian=tracked(parameters)
        initial_gates,gate_jacobian=gates(squared,jacobian)
        direction=np.random.default_rng(28640917+len(optimizations)).normal(size=len(parameters))
        direction/=np.linalg.norm(direction)
        increment=1e-4
        guard()
        plus=gates(model.evaluate(parameters+increment*direction,derivatives=False))[0]
        minus=gates(model.evaluate(parameters-increment*direction,derivatives=False))[0]
        numerical=(plus-minus)/(2*increment)
        analytic=gate_jacobian@direction
        error=float(np.linalg.norm(analytic-numerical)/max(np.linalg.norm(numerical),1e-30))
        gradient_checks.append({'phase':phase,'relative_directional_gate_jacobian_error':error,'passed':error<0.002})
        if error>=0.002:
            raise ArithmeticError('word-specific gate gradient check failed')
        vector=np.append(parameters,float(initial_gates.max())+0.01)
        cached_vector,cached_values,cached_derivative=None,None,None
        def constraints(vector):
            nonlocal cached_vector,cached_values,cached_derivative
            if cached_vector is not None and np.array_equal(vector,cached_vector):
                return cached_values
            squared,jacobian=tracked(vector[:-1])
            gate_values,gate_derivative=gates(squared,jacobian)
            cached_vector=vector.copy()
            cached_values=vector[-1]-gate_values
            cached_derivative=np.column_stack((-gate_derivative,np.ones(len(gate_values))))
            return cached_values
        def constraint_jacobian(vector):
            constraints(vector)
            return cached_derivative
        result=minimize(lambda vector:float(vector[-1]),vector,jac=lambda vector:np.r_[np.zeros(len(vector)-1),1.0],method='SLSQP',bounds=[(-12,12)]*len(parameters)+[(0.05,8.0)],constraints={'type':'ineq','fun':constraints,'jac':constraint_jacobian},options={'maxiter':maximum_iterations,'ftol':2e-9,'disp':False})
        optimizations.append({'phase':phase,'word':word,'message':str(result.message),'iterations':int(result.nit),'calls':int(result.nfev)})
        return result

    stop='neighborhood_completed'
    try:
        optimize(starting_word,starting_weights,80)
        base_word=list(best['word'])
        set_word(base_word)
        base_weights=model.decode(best['parameters'])[0]
        proposals=[]
        seen={tuple(base_word)}
        for first_index,second_index in itertools.combinations(range(17),2):
            word=list(base_word)
            weights=base_weights.copy()
            word[first_index],word[second_index]=word[second_index],word[first_index]
            weights[first_index],weights[second_index]=weights[second_index],weights[first_index]
            if tuple(word) in seen or any(left==right for left,right in zip(word,word[1:])):
                continue
            seen.add(tuple(word))
            proposals.append((f'swap_{first_index}_{second_index}',word,weights))
        for swap_axes,shift_x,shift_y in itertools.product((False,True),repeat=3):
            mapping={'V':'V'}
            for label in model.labels[:4]:
                axis=label[0]
                parity=int(label[1])^(shift_x if axis=='X' else shift_y)
                if swap_axes:
                    axis='Y' if axis=='X' else 'X'
                mapping[label]=axis+str(parity)
            word=[mapping[label] for label in base_word]
            if tuple(word) not in seen:
                proposals.append((f'lattice_symmetry_{swap_axes}_{shift_x}_{shift_y}',word,base_weights.copy()))
                seen.add(tuple(word))
        ranked=[]
        for origin,word,weights in proposals:
            phase='word_scan:'+origin
            set_word(word)
            parameters=model.encode(weights)
            squared,jacobian=tracked(parameters,derivatives=False)
            metrics=model.metrics(squared)
            ranked.append((metrics['maximum_gate_ratio'],origin,word,model.decode(parameters)[0]))
            scan.append({'origin':origin,**metrics})
        ranked.sort(key=lambda entry:entry[0])
        for rank,(violation,origin,word,weights) in enumerate(ranked[:8]):
            phase=f'word_opt_{rank}:'+origin
            optimize(word,weights,90)
    except ComputeLimit:
        stop='aggregate_compute_limit'
    except PassingMargin:
        stop='passing_margin_found'
    except ArithmeticError as error:
        stop='gradient_check_stopped: '+str(error)
    used_cpu=time.process_time()-started_cpu
    used_wall=time.monotonic()-started_wall
    set_word(best['word'])
    save('refined_submission.json',model.payload(best['parameters']))
    summary={'purpose':'private privileged exact refinement; no fresh-agent evidence','previous_optimization_cpu_seconds':consumed,'additional_cpu_budget_seconds':budget,'additional_optimization_cpu_seconds':used_cpu,'aggregate_optimization_cpu_seconds':consumed+used_cpu,'additional_optimization_wall_seconds':used_wall,'stop':stop,'best_metrics':best['metrics'],'best_word':best['word'],'word_candidates_scanned':len(scan),'optimizations':optimizations,'gradient_checks':gradient_checks,'scan':scan,'history':history,'protected_files_unchanged':protected_hashes()==before,'official_validation':'pending'}
    save('order_search_summary.json',summary)
    assert summary['aggregate_optimization_cpu_seconds']<600
    assert summary['protected_files_unchanged']
    print('ORDER_OPTIMIZATION_FINISHED',json.dumps({key:value for key,value in summary.items() if key not in ('history','scan','best_word')}),flush=True)
    process=subprocess.run([sys.executable,'-B',str(ROOT/'evaluator/evaluate.py'),'--submission',str(HERE/'refined_submission.json'),'--output',str(HERE/'refined_official_report.json')],text=True,capture_output=True,timeout=200)
    (HERE/'refined_official_stdout.log').write_text(process.stdout)
    (HERE/'refined_official_stderr.log').write_text(process.stderr)
    if process.returncode:
        summary['official_validation']='checker command failed: '+str(process.returncode)
    else:
        summary['official_validation']=json.loads((HERE/'refined_official_report.json').read_text())
        print('OFFICIAL_REPORT',json.dumps(summary['official_validation']),flush=True)
    summary['protected_files_unchanged']=protected_hashes()==before
    save('order_search_summary.json',summary)
    assert summary['protected_files_unchanged']


if __name__=='__main__':
    main()
