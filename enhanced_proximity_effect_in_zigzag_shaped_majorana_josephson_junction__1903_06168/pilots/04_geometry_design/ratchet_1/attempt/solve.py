#!/usr/bin/env python3
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
import argparse
import concurrent.futures
import copy
import json
from pathlib import Path
import signal
import sys
import time

import numpy as np
from physics import ForwardModel, feasibility, geometry_digest
from fast_physics import Spectrum
from geometry import make_geometry
from gradient import derivatives, boundary_candidates


COARSE = (0, 12, 25, 38, 50)
MEDIUM = (0, 6, 12, 19, 25, 31, 38, 44, 50)


class Deadline(Exception):
    pass


def expired(signum, frame):
    raise Deadline()


def evaluate(request, record, indices, deadline, scenario_indices=None):
    result = copy.deepcopy(record)
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.01, deadline-time.monotonic()))
    try:
        for point_index in range(len(request['operating_points'])) if scenario_indices is None else scenario_indices:
            if time.monotonic() > deadline-1:
                break
            previous = result['samples'].get(point_index, {})
            if previous.get('invariant') == -1 and all(index in previous.get('values', {}) for index in indices):
                continue
            spectrum = Spectrum(ForwardModel(request, result['masks'], request['operating_points'][point_index]))
            spectrum.signs.update(previous.get('signs', {}))
            spectrum.values.update({index*np.pi/50: value for index,value in previous.get('values',{}).items()})
            sample = dict(invariant=spectrum.invariant(True), signs=spectrum.signs, values={})
            result['samples'][point_index] = sample
            for endpoint in (0, 50):
                sample['values'][endpoint] = spectrum.gap(endpoint*np.pi/50)
            sample['values'].update(previous.get('values', {}))
            if sample['invariant'] != -1:
                result['rejected'] = True
                break
            for index in indices:
                if time.monotonic() > deadline-1:
                    break
                sample['values'][index] = spectrum.gap(index*np.pi/50)
    except Deadline:
        pass
    except Exception as error:
        result['rejected'] = True
        result['error'] = str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    return result


def derivative_job(request, masks, scenario, momenta, deadline):
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.01,deadline-time.monotonic()))
    try:
        return derivatives(request,masks,scenario,momenta)
    except Exception:
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)


def gaps(record, count):
    if record.get('rejected'):
        return None
    values = []
    for point_index in range(count):
        sample = record['samples'].get(point_index,{})
        if sample.get('invariant') != -1 or not sample.get('values'):
            return None
        values.append(min(sample['values'].values()))
    return values if min(values) > 1e-5 else None


def merit(record, count):
    values = gaps(record,count)
    return .5*float(np.mean(values))+.5*min(values) if values else -1.0


def complete(record, count, indices):
    return all(all(index in record['samples'].get(point_index,{}).get('values',{}) for index in indices)
               for point_index in range(count))


def write_result(request, masks, output):
    result = dict(schema_version=1,request_id=request['request_id'],
                  geometry={name:mask.astype(int).tolist() for name,mask in masks.items()})
    temporary = output.with_name(output.name+'.tmp')
    with temporary.open('w',encoding='utf-8') as handle:
        json.dump(result,handle,separators=(',',':'),allow_nan=False)
    os.replace(temporary,output)


class Search:
    def __init__(self,request,pool,workers,started,duration,output):
        self.request = request
        self.pool = pool
        self.workers = workers
        self.started = started
        self.duration = duration
        self.deadline = started+duration
        self.output = output
        self.records = {}
        self.count = len(request['operating_points'])

    def add(self,parameters=None,masks=None,label=None):
        if masks is None:
            masks = make_geometry(self.request,parameters)
        if not feasibility(self.request,masks)['valid']:
            return None
        digest = geometry_digest(masks)
        if digest in self.records:
            return None
        record = dict(digest=digest,parameters=parameters,masks=masks,samples={},label=label)
        self.records[digest] = record
        return record

    def run(self,candidates,indices=(0,50),until=None):
        deadline = min(self.deadline,until or self.deadline)
        iterator = iter(candidates)
        pending = {}
        exhausted = False
        results = []
        while pending or not exhausted:
            while len(pending) < self.workers and not exhausted and time.monotonic() < deadline-3:
                candidate = next(iterator,None)
                if candidate is None:
                    exhausted = True
                    break
                candidate = self.records[candidate['digest']]
                if candidate.get('rejected') or complete(candidate,self.count,indices):
                    continue
                future = self.pool.submit(evaluate,self.request,candidate,indices,deadline)
                pending[future] = candidate['digest']
            if not pending:
                break
            finished,_ = concurrent.futures.wait(pending,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                digest = pending.pop(future)
                try:
                    record = future.result()
                    self.records[digest] = record
                    results.append(record)
                except Exception as error:
                    self.records[digest]['rejected'] = True
                    self.records[digest]['error'] = str(error)
            if time.monotonic() >= deadline-3:
                exhausted = True
        return results

    def ranked(self,indices=(0,50)):
        return sorted((record for record in self.records.values()
                       if merit(record,self.count)>0 and complete(record,self.count,indices)),
                      key=lambda record:merit(record,self.count),reverse=True)

    def checkpoint(self,indices=COARSE,label='Search'):
        leaders = self.ranked(indices)
        if leaders:
            best = leaders[0]
            write_result(self.request,best['masks'],self.output)
            print(f'{label}: {time.monotonic()-self.started:.1f}s; {len(self.records)} layouts; '
                  f'R={merit(best,self.count):.8f}; gaps={gaps(best,self.count)}; '
                  f'parameters={best["parameters"]}; {best["label"]}',file=sys.stderr,flush=True)
        return leaders


def seeds():
    yield dict(frequency=3,amplitude=205.4,width=110.9,rounding=.676,third=.8)
    yield dict(frequency=3,amplitude=200,width=110)
    yield dict(frequency=3,amplitude=180,width=120)
    yield dict(frequency=3,amplitude=220,width=105)
    yield dict(frequency=2,amplitude=140,width=90)
    for frequency,amplitudes in ((3,(140,180,220,260)),(2,(120,160,200)),(4,(140,220)),(5,(120,200))):
        for amplitude in amplitudes:
            for width in (95,115,135):
                yield dict(frequency=frequency,amplitude=amplitude,width=width)
    for rounding in (-.2,.25,.6,1.0):
        for amplitude in (180,220):
            yield dict(frequency=3,amplitude=amplitude,width=110,rounding=rounding)


def neighbors(parameters,generator,scale=1.0):
    bounds = {'amplitude':(60,320),'width':(80,180),'rounding':(-.35,1.2),
              'modulation':(-30,30),'third':(-40,40)}
    scales = {'amplitude':20,'width':10,'rounding':.2,'modulation':8,'third':10}
    names = list(bounds)
    for name in names:
        for direction in (-1,1):
            candidate = dict(parameters)
            candidate[name] = float(np.clip(candidate.get(name,0)+direction*scales[name]*scale,*bounds[name]))
            yield candidate
    for number in range(8):
        candidate = dict(parameters)
        for name in generator.choice(names,size=2,replace=False):
            candidate[name] = float(np.clip(candidate.get(name,0)+generator.normal()*scales[name]*scale,*bounds[name]))
        yield candidate


def solve(request,output,started):
    wall = float(request.get('budget',{}).get('wall_seconds',1200))
    duration = min(1135.0,max(10.0,wall-50))
    duration = min(duration,float(os.environ.get('SOLVE_SECONDS',duration)))
    workers = max(1,min(2,int(request.get('budget',{}).get('cpu_cores',2))))
    initial = make_geometry(request,None)
    write_result(request,initial,output)
    generator = np.random.RandomState(3917)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        search = Search(request,pool,workers,started,duration,output)
        baseline = search.add()
        candidates = [baseline]+[record for parameters in seeds() if (record:=search.add(parameters)) is not None]
        search.run(candidates,until=started+.20*duration)
        search.checkpoint((0,50),'Global search')
        for iteration in range(3):
            leaders = [record for record in search.ranked() if record['parameters'] is not None][:3]
            candidates = []
            for leader in leaders:
                for parameters in neighbors(leader['parameters'],generator,scale=.8**iteration):
                    record = search.add(parameters)
                    if record is not None:
                        candidates.append(record)
            search.run(candidates,until=started+.34*duration)
            if time.monotonic() >= started+.34*duration-3:
                break
        search.run(search.ranked()[:5],COARSE,until=started+.45*duration)
        leaders = search.checkpoint(COARSE,'Momentum screening')
        iteration = 0
        while leaders and time.monotonic() < started+.71*duration-25:
            leader = leaders[0]
            jobs = []
            for point_index,scenario in enumerate(request['operating_points']):
                values = leader['samples'][point_index]['values']
                minimum = min(values,key=values.get)
                momenta = [0.0,np.pi]
                if minimum not in (0,50):
                    momenta.append(minimum*np.pi/50)
                jobs.append(pool.submit(derivative_job,request,leader['masks'],scenario,momenta,started+.71*duration))
            samples = [future.result() for future in jobs]
            if any(sample is None for sample in samples):
                break
            candidates = []
            for masks in boundary_candidates(request,leader['masks'],samples,counts=(2,4,8),singles=12):
                record = search.add(masks=masks,label=f'boundary iteration {iteration+1}')
                if record is not None:
                    candidates.append(record)
            search.run(candidates,until=started+.71*duration)
            promising = sorted((search.records[record['digest']] for record in candidates),
                               key=lambda record:merit(record,search.count),reverse=True)
            promising = [record for record in promising if merit(record,search.count)>merit(leader,search.count)+1e-6]
            if not promising:
                break
            search.run(promising[:2],COARSE,until=started+.71*duration)
            leaders = search.checkpoint(COARSE,f'Boundary refinement {iteration+1}')
            iteration += 1
            if not leaders or leaders[0]['digest'] == leader['digest']:
                break
        search.run(search.ranked(COARSE)[:2],MEDIUM,until=started+.83*duration)
        leaders = search.checkpoint(MEDIUM,'Dense screening')
        if not leaders:
            leaders = search.ranked(COARSE) or search.ranked()
        if not leaders:
            return
        best = leaders[0]
        jobs = [pool.submit(evaluate,request,best,tuple(range(51)),search.deadline-5,[point_index])
                for point_index in range(search.count)]
        for future in concurrent.futures.as_completed(jobs):
            partial = future.result()
            if partial.get('rejected'):
                best['rejected'] = True
            for point_index,sample in partial['samples'].items():
                if len(sample.get('values',{}))>len(best['samples'].get(point_index,{}).get('values',{})):
                    best['samples'][point_index] = sample
        search.records[best['digest']] = best
        if merit(best,search.count)>0:
            write_result(request,best['masks'],output)
            print(f'Final: R={merit(best,search.count):.8f}; gaps={gaps(best,search.count)}; '
                  f'momenta={[len(best["samples"][point_index]["values"]) for point_index in range(search.count)]}; '
                  f'elapsed={time.monotonic()-started:.1f}s',file=sys.stderr,flush=True)
        else:
            alternatives = [record for record in search.ranked(MEDIUM) if record['digest']!=best['digest']]
            if alternatives:
                write_result(request,alternatives[0]['masks'],output)
            else:
                write_result(request,initial,output)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description='Full-scale topological Josephson contact optimization')
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    arguments = parser.parse_args()
    with open(arguments.input,encoding='utf-8') as handle:
        request = json.load(handle)
    solve(request,Path(arguments.output),started)


if __name__=='__main__':
    main()
