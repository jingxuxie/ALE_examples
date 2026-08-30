import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from build_package import ROOT, put, wide_artifact
from evaluate import HIDDEN, build, measure, evaluate
sys.path.insert(0,str(HIDDEN))
from oracle import check

TOLERANCES = {'momentum_atol':3e-9,'shell_atol':3e-10,'conservation_atol':3e-11,
              'mapped_invariant_atol':3e-9,'invariant_rtol':3e-8,'invariant_atol':1e-29,
              'rotation_atol':3e-12,'timing_repeats':300}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def freeze():
    if (HIDDEN/'target.json').exists():
        raise RuntimeError('Target already frozen')
    cases = json.loads((HIDDEN/'cases.json').read_text())
    references = json.loads((HIDDEN/'references.json').read_text())
    timings = {}
    reports = {}
    for name,path in [('baseline',ROOT/'participant/baseline'),('full_quad',HIDDEN/'cost_reference')]:
        with tempfile.TemporaryDirectory(prefix='eerad3-calibrate-') as directory:
            executable = build(path,directory)
            records,seconds,trials = measure(executable,cases,TOLERANCES['timing_repeats'])
        failures = [{'id':case['id'],'checks':check(case,reference,record,TOLERANCES)}
                    for case,reference,record in zip(cases,references,records)]
        failures = [failure for failure in failures if failure['checks']]
        timings[name] = {'median_cpu_seconds':seconds,'trials':trials}
        reports[name] = {'failed_case_count':len(failures),'failures':failures}
    print(json.dumps({'timings':timings,'reports':reports},indent=2),flush=True)
    if reports['full_quad']['failures']:
        raise AssertionError('Reference must be numerically validated before target freeze')
    if not reports['baseline']['failures']:
        raise AssertionError('Baseline unexpectedly passes')
    ratio = timings['full_quad']['median_cpu_seconds']/timings['baseline']['median_cpu_seconds']
    limit = min(18.,.60*ratio)
    if limit <= 1.5:
        raise AssertionError('Insufficient real cost separation; do not create an artificial floor')
    target = dict(TOLERANCES,runtime_ratio_limit=limit,freeze_utc=stamp(),
        case_sha256=hashlib.sha256((HIDDEN/'cases.json').read_bytes()).hexdigest(),
        reference_sha256=hashlib.sha256((HIDDEN/'references.json').read_bytes()).hexdigest(),
        calibration=timings,calibration_policy='min(18,0.60*full_quad_cpu/baseline_cpu)',baseline_must_fail=True)
    put('evaluator/hidden/target.json',json.dumps(target,indent=2)+'\n')
    put('evaluator/hidden/calibration_checks.json',json.dumps(reports,indent=2)+'\n')
    put('participant/input/RESOURCE.json',json.dumps({'runtime_ratio_limit':limit,
        'metric':'median kernel CPU seconds / same-host baseline median, three trials',
        'absolute_runtime_floor':None,'freeze_utc':target['freeze_utc']},indent=2)+'\n')


def mutate(name, edits):
    source = ROOT/'champions/selective_precision'
    for filename in ['kinematics.f','phaseee.f','eerad3lib.f','driver.f90','Makefile']:
        text = (source/filename).read_text()
        for target_file,before,after in edits:
            if filename == target_file:
                if before not in text:
                    raise RuntimeError(f'Mutation not found: {name}/{filename}')
                text = text.replace(before,after)
        put(Path('adversary')/name/filename,text)


def validate():
    if not (HIDDEN/'target.json').exists():
        raise RuntimeError('Target must already be frozen')
    frozen_hash = hashlib.sha256((HIDDEN/'target.json').read_bytes()).hexdigest()
    wide_artifact(Path('champions/selective_precision'),True)
    mutate('naive_dot',[('eerad3lib.f','dot=alen*blen*chord/2d0','dot=a(4)*b(4)-sum(a(1:3)*b(1:3))'),
                        ('eerad3lib.f','if (.false..or.chord.lt.1d-8) then','if (.false.) then')])
    mutate('no_mapping_fallback',[('kinematics.f','if (.true..and.y(i1,i4).gt.1d-5) then','if (.true.) then')])
    mutate('discard_small_invariants',[('phaseee.f','sij(j,i) = sij(i,j)',
        'if (abs(sij(i,j)).lt.1d-14*sum(p(4,:))**2)\n     &           sij(i,j)=0d0\n            sij(j,i) = sij(i,j)')])
    mutate('identity_rotation',[('phaseee.f','largest=maxval(abs(a(1:3)))','largest=0d0')])
    mutate('broken_mapmomenta',[('kinematics.f','p3=ppar(:,1:3)','p3=0d0'),
                              ('kinematics.f','p3(i,j1) = ppar(i,j1)','p3(i,j1) = 0d0')])
    mutate('wrong_branch',[('kinematics.f','rho = sqrt(rho2)','rho = -sqrt(rho2)')])
    mutate('renormalize_only',[('kinematics.f','p3=ppar(:,1:3)',
        'ppar(1:3,1)=ppar(1:3,1)*1.00001d0\n      ppar(4,1)=norm2(ppar(1:3,1))\n      p3=ppar(:,1:3)')])
    artifacts = [('baseline',ROOT/'participant/baseline'),('selective_precision',ROOT/'champions/selective_precision'),
                 ('blanket_quad',HIDDEN/'cost_reference')]
    artifacts += [(name,ROOT/'adversary'/name) for name in ['naive_dot','no_mapping_fallback','discard_small_invariants',
        'identity_rotation','broken_mapmomenta','wrong_branch','renormalize_only']]
    results = {}
    for name,path in artifacts:
        result = evaluate(path)
        result['validation_utc'] = stamp()
        put(Path('attempts')/(name+'.json'),json.dumps(result,indent=2)+'\n')
        results[name] = {key:result[key] for key in ['core_score','worst_family_score','runtime_score','passed','reason']}
        print(name,json.dumps(results[name]),flush=True)
    if not results['selective_precision']['passed']:
        raise AssertionError('Private feasibility witness has not passed')
    if any(result['passed'] for name,result in results.items() if name != 'selective_precision'):
        raise AssertionError('Negative control unexpectedly passes')
    if results['blanket_quad']['core_score'] != 1.:
        raise AssertionError('Blanket quad should fail only on cost')
    assert hashlib.sha256((HIDDEN/'target.json').read_bytes()).hexdigest() == frozen_hash
    result = {'status':'ready','concept':'concept_3','mode':'F','scope':'native DAK2 five-to-three mapping, invariants and rotations',
        'fresh_agents_launched':0,'frozen_target_sha256':frozen_hash,'validated_utc':stamp(),
        'participant_path':'participant','private_passing_artifact':'champions/selective_precision',
        'scores':results,'known_unknowns':['Compiler/CPU portability beyond GNU Fortran 11 on this Linux host is not measured.',
        'Finite hidden corpus, not a proof over the continuum; exact degenerate antennae are outside the contract.',
        'All-wide arithmetic has a measured cost rejection; a sufficiently fast wide implementation remains eligible.',
        'Bubblewrap requires outer sandbox escalation on hosts blocking NETLINK_ROUTE; network isolation is mandatory.']}
    put('status.json',json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['freeze','validate'])
    args = parser.parse_args()
    freeze() if args.mode == 'freeze' else validate()
