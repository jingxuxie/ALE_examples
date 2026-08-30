import sys, random, time, math, json
sys.path.insert(0, '/tmp/cascade-c3-g2-v2-0f0el7m5/participant/input')
from simulator import Device, component_edges

def template(family):
    graph = [[] for _ in range(32)]
    for block, kind in enumerate(family):
        for first, second in component_edges(kind):
            first += 16 * block
            second += 16 * block
            graph[first].append(second)
            graph[second].append(first)
    return graph

TEMPLATES = {kind: template(kind) for kind in ('RR','RS','SS')}

def fit(counts, family, runs=30, iterations=6000):
    graph = TEMPLATES[family]
    rng = random.Random(452)
    rand = rng.random
    randint = rng.randrange
    best = -1
    solutions = []
    for run in range(runs):
        labels = list(range(32))
        if solutions and run % 3:
            labels = list(solutions[randint(min(5,len(solutions)))][1])
            for repeat in range(6):
                first, second = randint(32),randint(32)
                labels[first],labels[second] = labels[second],labels[first]
        else:
            rng.shuffle(labels)
        score = sum(counts[labels[first]][labels[second]] for first in range(32) for second in graph[first]) / 2
        for iteration in range(iterations):
            first = randint(32)
            second = randint(31)
            if second >= first: second += 1
            left, right = labels[first],labels[second]
            delta = 0
            for neighbor in graph[first]:
                if neighbor != second:
                    site = labels[neighbor]
                    delta += counts[right][site] - counts[left][site]
            for neighbor in graph[second]:
                if neighbor != first:
                    site = labels[neighbor]
                    delta += counts[left][site] - counts[right][site]
            temperature = 1.2 * (1 - iteration/iterations)**2 + .07
            if delta >= 0 or rand() < math.exp(delta / temperature):
                labels[first],labels[second] = right,left
                score += delta
            if score > best:
                best = score
                best_labels = list(labels)
        solutions.append((score,list(labels)))
        solutions.sort(reverse=True)
        solutions = solutions[:10]
    return best,best_labels

def test(number=9, frames=96, runs=30, iterations=6000):
    cases=json.load(open('/tmp/cascade-c3-g2-v2-0f0el7m5/participant/input/dev_cases.json'))
    for case in cases[:number]:
        device = Device(case['family'],case['contamination_denominator'],case['seed'])
        counts=[[0]*32 for _ in range(32)]
        for frame in range(frames):
            source=frame%32
            device.handle({'op':'start','source':source})
            echo=next(site for site in range(32) if site!=source and device.residual >> (8*site)&255)
            counts[source][echo]+=1
            counts[echo][source]+=1
        started=time.process_time()
        scores={kind:fit(counts,kind,runs,iterations)[0] for kind in TEMPLATES}
        true_score=sum(counts[first][second] for first in range(32) for second in device.neighbors[first])/2
        print(case['family'],case['contamination_denominator'],scores,'true',true_score,'cpu',round(time.process_time()-started,2),flush=True)

if __name__=='__main__':
    test(*map(int,sys.argv[1:]))
