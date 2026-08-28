#!/usr/bin/env python3
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time

import numpy as np
from threadpoolctl import threadpool_limits

for directory in (Path.cwd() / 'workspace', Path(__file__).resolve().parent.parent / 'participant' / 'workspace'):
    if (directory / 'physics.py').is_file():
        sys.path.insert(0, str(directory))
        break
from physics import ForwardModel, feasibility, geometry_digest
from fast_physics import Spectrum
from geometry import initial_parameters, make_geometry, neighbors


PRIMARY = [(0.15, 0.15), (0.5, 0.5), (0.85, 0.85)]
REGION = [(chemical, field) for chemical in (0.15, 0.5, 0.85) for field in (0.15, 0.5, 0.85)]
VALIDATION = sorted(set(REGION + [(chemical, field) for chemical in (0.05, 0.3, 0.7, 0.95) for field in (0.1, 0.5, 0.9)]))
TOPOLOGY = [(chemical, field) for chemical in np.linspace(0, 1, 9) for field in np.linspace(0, 1, 5)]


def scenario(request, coordinates):
    region = request['operating_region']
    chemical, field = coordinates
    mu_lower, mu_upper = region['mu_normal_mev']
    field_lower, field_upper = region['zeeman_mev']
    return dict(mu_normal_mev=mu_lower + chemical * (mu_upper - mu_lower),
                zeeman_mev=field_lower + field * (field_upper - field_lower))


def evaluate(request, record, coordinates, count, deadline):
    record = dict(record)
    record['samples'] = dict(record.get('samples', {}))
    try:
        masks = make_geometry(request, record['parameters'])
        with threadpool_limits(limits=1):
            for point in coordinates:
                if time.monotonic() > deadline - 2:
                    break
                previous = record['samples'].get(point, {})
                if previous.get('invariant') == 1:
                    record['rejected'] = True
                    break
                if count == 0 and 'invariant' in previous:
                    continue
                if count and all(float(momentum) in previous.get('values', {}) for momentum in np.linspace(0, np.pi, count)):
                    continue
                spectrum = Spectrum(ForwardModel(request, masks, scenario(request, point)))
                spectrum.values.update(previous.get('values', {}))
                spectrum.signs.update(previous.get('signs', {}))
                invariant = spectrum.invariant(with_gap=count > 0)
                if invariant == -1 and count:
                    spectrum.scan(count)
                    if count >= 9:
                        spectrum.refine()
                record['samples'][point] = dict(invariant=invariant, values=spectrum.values, signs=spectrum.signs)
                if invariant != -1:
                    record['rejected'] = True
                    break
    except Exception as error:
        record['error'] = str(error)
        record['rejected'] = True
    return record


def merit(record, coordinates):
    if record.get('rejected'):
        return -1.0
    gaps = []
    for point in coordinates:
        sample = record.get('samples', {}).get(point)
        if sample is None or sample.get('invariant') != -1 or not sample.get('values'):
            return -1.0
        gaps.append(min(sample['values'].values()))
    if min(gaps) <= 1e-5:
        return -1.0
    return float(0.5 * np.mean(gaps) + 0.5 * min(gaps))


class Search:
    def __init__(self, request, pool, started, duration):
        self.request = request
        self.pool = pool
        self.started = started
        self.deadline = started + duration
        self.records = {}

    def add(self, parameters):
        masks = make_geometry(self.request, parameters)
        if not feasibility(self.request, masks)['valid']:
            return None
        digest = geometry_digest(masks)
        if digest in self.records:
            return None
        record = dict(digest=digest, parameters=parameters, samples={})
        self.records[digest] = record
        return record

    def run(self, candidates, coordinates, count=5, until=None):
        deadline = min(self.deadline, until or self.deadline)
        iterator = iter(candidates)
        running = {}
        exhausted = False
        results = []
        while running or not exhausted:
            while len(running) < 2 and not exhausted and time.monotonic() < deadline - 4:
                candidate = next(iterator, None)
                if candidate is None:
                    exhausted = True
                    break
                future = self.pool.submit(evaluate, self.request, candidate, coordinates, count, deadline)
                running[future] = candidate['digest']
            if not running:
                break
            completed, _ = concurrent.futures.wait(running, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in completed:
                digest = running.pop(future)
                try:
                    result = future.result()
                    self.records[digest] = result
                    results.append(result)
                except Exception as error:
                    self.records[digest]['rejected'] = True
                    self.records[digest]['error'] = str(error)
            if time.monotonic() >= deadline - 4:
                exhausted = True
        return results

    def ranked(self, coordinates):
        return sorted((record for record in self.records.values() if merit(record, coordinates) > 0),
                      key=lambda record: merit(record, coordinates), reverse=True)

    def report(self, label, coordinates):
        ranked = self.ranked(coordinates)
        if ranked:
            print(f'{label}: {len(self.records)} geometries, {time.monotonic() - self.started:.1f}s, '
                  f'robust gap {merit(ranked[0], coordinates):.6f}, {ranked[0]["parameters"]}', file=sys.stderr, flush=True)


def write_result(request, parameters, output):
    masks = make_geometry(request, parameters)
    result = dict(schema_version=1, request_id=request['request_id'],
                  geometry={name: mask.astype(int).tolist() for name, mask in masks.items()})
    output = Path(output)
    temporary = output.with_name(output.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(result, handle, separators=(',', ':'), allow_nan=False)
    os.replace(temporary, output)


def solve(request, output, started):
    wall = float(request.get('budget', {}).get('wall_seconds', 1200))
    duration = max(15, min(wall - 45, 1120))
    write_result(request, None, output)
    generator = np.random.RandomState(3917)
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        search = Search(request, pool, started, duration)
        candidates = [record for parameters in initial_parameters(request) if (record := search.add(parameters)) is not None]
        search.run(candidates, PRIMARY, until=started + 0.33 * duration)
        search.report('Initial search', PRIMARY)
        leaders = search.ranked(PRIMARY)[:12]
        search.run(leaders, REGION, until=started + 0.48 * duration)
        search.report('Operating-region screening', REGION)
        iteration = 0
        while time.monotonic() < started + 0.76 * duration and iteration < 5:
            leaders = search.ranked(REGION)
            if not leaders:
                break
            candidates = []
            for leader in leaders[:3]:
                for parameters in neighbors(leader['parameters'], generator, 14):
                    record = search.add(parameters)
                    if record is not None:
                        candidates.append(record)
            if not candidates:
                break
            search.run(candidates, PRIMARY, until=started + 0.69 * duration)
            promising = [record for record in search.ranked(PRIMARY)
                         if merit(record, REGION) < 0 and not record.get('rejected')][:10]
            search.run(promising, REGION, until=started + 0.78 * duration)
            search.report(f'Boundary refinement {iteration + 1}', REGION)
            iteration += 1
            if time.monotonic() >= started + 0.69 * duration:
                break
        leaders = search.ranked(REGION)[:6]
        for offset in range(0, len(leaders), 2):
            search.run(leaders[offset:offset + 2], TOPOLOGY, count=0, until=started + 0.87 * duration)
            checked = [record for record in search.ranked(REGION)
                       if all(record.get('samples', {}).get(point, {}).get('invariant') == -1 for point in TOPOLOGY)]
            if len(checked) >= 2:
                break
        leaders = [record for record in search.ranked(REGION)
                   if all(record.get('samples', {}).get(point, {}).get('invariant') == -1 for point in TOPOLOGY)][:2]
        search.run(leaders, VALIDATION, count=5, until=search.deadline - 10)
        finalists = search.ranked(VALIDATION)[:2]
        search.run(finalists, VALIDATION, count=9, until=search.deadline - 10)
        validated = search.ranked(VALIDATION)
        if validated:
            best = validated[0]
        else:
            checked = [record for record in search.ranked(REGION)
                       if all(record.get('samples', {}).get(point, {}).get('invariant') == -1 for point in TOPOLOGY)]
            alternatives = checked or search.ranked(REGION) or search.ranked(PRIMARY)
            best = alternatives[0] if alternatives else dict(parameters=None)
        write_result(request, best['parameters'], output)
        search.report('Final validation', VALIDATION)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description='Robust periodic Josephson contact design')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    with open(arguments.input, encoding='utf-8') as handle:
        request = json.load(handle)
    solve(request, arguments.output, started)


if __name__ == '__main__':
    main()
