from collections import deque
import numpy as np


def transitions(problem, state):
    indices = np.flatnonzero(abs(state) > 1e-9)
    inverse = {index: position for position, index in enumerate(indices)}
    options = []
    seen = set()
    for label, (sources, destinations, signs) in enumerate(problem.pairs):
        forbidden = 0
        links = []
        for source, destination in zip(sources, destinations):
            if source in inverse and destination in inverse:
                links.append((1 << inverse[source], 1 << inverse[destination]))
            elif source in inverse:
                forbidden |= 1 << inverse[source]
            elif destination in inverse:
                forbidden |= 1 << inverse[destination]
        key = (forbidden, tuple(links))
        if links and key not in seen:
            options.append((forbidden, links))
            seen.add(key)
    return len(indices), options


def bound(problem, state, limit=10, cap=200000):
    size, options = transitions(problem, state)
    goal = (1 << size) - 1
    visited = {1 << position for position in range(size)}
    frontier = list(visited)
    for depth in range(1, limit + 1):
        following = []
        for current in frontier:
            for forbidden, links in options:
                if current & forbidden:
                    continue
                after = current
                for source, destination in links:
                    if current & source:
                        after |= destination
                    if current & destination:
                        after |= source
                if after == goal:
                    return depth, len(visited)
                if after not in visited:
                    visited.add(after)
                    following.append(after)
        frontier = following
        if not frontier:
            return 100, len(visited)
        if len(visited) > cap:
            return -depth, len(visited)
    return limit + 1, len(visited)


if __name__ == '__main__':
    from beam import Problem, load_cases
    problem = Problem(load_cases()[1])
    for depth in (10, 11, 12, 13, 14):
        data = np.load(f'beam_1_sym_{depth}.npz')
        for parent, state in enumerate(data['states'][:5]):
            print(depth, parent, np.count_nonzero(abs(state) > 1e-9), bound(problem, state, 18 - depth), flush=True)
