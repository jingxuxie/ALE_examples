import itertools, random, math, sys, time

def structures():
    result=[]
    for partners in itertools.combinations(range(1,6),2):
        group=(0,)+partners
        other=tuple(site for site in range(6) if site not in group)
        edges=list(itertools.combinations(group,2))+list(itertools.combinations(other,2))
        result.append(('R',edges))
    for order in itertools.permutations(range(1,6)):
        if order[0]>order[-1]: continue
        cycle=(0,)+order
        result.append(('S',[(cycle[index],cycle[(index+1)%6]) for index in range(6)]))
    return result

STRUCTURES=structures()

def trial(seed, frames=50, contamination=.25, active=True):
    rng=random.Random(seed)
    family=rng.randrange(2)
    actual=rng.randrange(10) if family==0 else rng.randrange(10,70)
    probabilities=[]
    for kind,edges in STRUCTURES:
        matrix=[[contamination/31]*6 for _ in range(6)]
        for site in range(6): matrix[site][site]=0
        for first,second in edges:
            matrix[first][second]+=(1-contamination)/6
            matrix[second][first]+=(1-contamination)/6
        for site in range(6): matrix[site].append(1-sum(matrix[site]))
        probabilities.append(matrix)
    weights=[.05]*10+[1/120]*60
    for frame in range(frames):
        family_weight=sum(weights[:10])
        if active:
            best=-1
            for source in range(6):
                left=[sum(weights[index]*probabilities[index][source][target] for index in range(10)) for target in range(7)]
                right=[sum(weights[index]*probabilities[index][source][target] for index in range(10,70)) for target in range(7)]
                score=sum(value*math.log(value/(prior*(left[target]+right[target]))) for values,prior in ((left,family_weight),(right,1-family_weight)) for target,value in enumerate(values) if value>0)
                if score>best: best=score; chosen=source
        else: chosen=frame%6
        threshold=rng.random()
        outcome=6
        for target,probability in enumerate(probabilities[actual][chosen]):
            threshold-=probability
            if threshold<0: outcome=target; break
        weights=[weight*probabilities[index][chosen][outcome] for index,weight in enumerate(weights)]
        total=sum(weights)
        weights=[weight/total for weight in weights]
    return (sum(weights[:10])>.5)==(family==0), family

if __name__=='__main__':
    number=int(sys.argv[1]) if len(sys.argv)>1 else 100
    frames=int(sys.argv[2]) if len(sys.argv)>2 else 50
    total=[0,0]; correct=[0,0]
    started=time.time()
    for seed in range(number):
        good,family=trial(seed,frames)
        total[family]+=1; correct[family]+=good
    print(frames,correct,total,time.time()-started,flush=True)
