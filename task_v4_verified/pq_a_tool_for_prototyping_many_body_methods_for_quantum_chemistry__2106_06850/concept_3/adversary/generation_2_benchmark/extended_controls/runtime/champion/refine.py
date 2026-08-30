from continuous import *
import argparse


def proposal_list(model, labels, angles, per_position=4):
    case = model.case
    history = [reference_state(case)]
    for label, theta in zip(labels, angles):
        history.append(apply_rotation(history[-1], model.pairs[label], theta))
    backwards = [None] * (len(labels)+1)
    backwards[-1] = case.target.copy()
    for position in reversed(range(len(labels))):
        backwards[position] = apply_rotation(backwards[position+1], model.pairs[labels[position]], -angles[position])
    proposals = []
    for position in range(len(labels)):
        source = history[position]
        target = backwards[position+1]
        base_overlap = float(target @ source)
        options = []
        for label, pairs in enumerate(model.pairs):
            if label == labels[position]:
                continue
            sources, destinations, signs = pairs
            active = float(target[sources]@source[sources]+target[destinations]@source[destinations])
            tangent = float(target[destinations]@(signs*source[sources])-target[sources]@(signs*source[destinations]))
            constant = base_overlap-active
            theta = math.atan2(tangent,active)
            radius = math.hypot(tangent,active)
            if constant < 0:
                theta = (theta+2*math.pi)%(2*math.pi)-math.pi
            overlap = abs(constant)+radius
            options.append((1-overlap**2, position, label, theta))
        options.sort()
        proposals.extend(options[:per_position])
    return sorted(proposals)


def write_candidate(case, model, labels, angles, loss):
    payload = {'case_id':case.case_id,'gates':[{'annihilate':list(model.labels[label].annihilate),'create':list(model.labels[label].create),'theta':float(theta)} for label,theta in zip(labels,angles)]}
    Path('refined104.json').write_text(json.dumps(payload,indent=2)+'\n')
    print('BEST',len(labels),'loss',loss,'fidelity',1-loss+loss**2/4,flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed',default='seed104.json')
    parser.add_argument('--iterations',type=int,default=100)
    parser.add_argument('--random',type=int,default=1)
    args = parser.parse_args()
    case = load_cases()[0]
    model = Model(case)
    random = np.random.default_rng(args.random)
    data = json.loads(Path(args.seed).read_text())
    if 'reverse' in data:
        gates = from_reverse(case, data)
    else:
        gates = [(Excitation(tuple(gate['annihilate']),tuple(gate['create'])),gate['theta']) for gate in data['gates']]
    labels = np.asarray([model.labels.index(label) for label,theta in gates],dtype=np.int32)
    angles = np.asarray([theta for label,theta in gates])
    loss, angles = model.fit(labels,angles,300)
    print('INITIAL',len(labels),loss,flush=True)
    while len(labels)>case.max_gates:
        options = []
        for position in range(len(labels)):
            candidate_labels = np.delete(labels,position)
            candidate_loss, candidate_angles = model.fit(candidate_labels,np.delete(angles,position),150)
            options.append((candidate_loss,position,candidate_angles))
        loss, position, angles = min(options,key=lambda entry:entry[0])
        labels = np.delete(labels,position)
        print('PRUNE',len(labels),loss,flush=True)
    best = loss, labels.copy(), angles.copy()
    write_candidate(case,model,labels,angles,loss)
    started = time.perf_counter()
    stale = 0
    for iteration in range(args.iterations):
        proposals = proposal_list(model,labels,angles,4)
        options = [(loss,labels,angles)]
        for local_loss,position,label,theta in proposals:
            candidate_labels = labels.copy()
            candidate_labels[position] = label
            candidate_angles = angles.copy()
            candidate_angles[position] = theta
            candidate_loss, candidate_angles = model.fit(candidate_labels,candidate_angles,100)
            options.append((candidate_loss,candidate_labels,candidate_angles))
        for position in range(len(labels)-1):
            candidate_labels = labels.copy()
            candidate_angles = angles.copy()
            candidate_labels[position:position+2] = candidate_labels[position:position+2][::-1]
            candidate_angles[position:position+2] = candidate_angles[position:position+2][::-1]
            candidate_loss,candidate_angles = model.fit(candidate_labels,candidate_angles,100)
            options.append((candidate_loss,candidate_labels,candidate_angles))
        new_loss,new_labels,new_angles = min(options,key=lambda entry:entry[0])
        if new_loss < loss-1e-10:
            loss,labels,angles = new_loss,new_labels,new_angles
            stale = 0
        else:
            stale += 1
            options.sort(key=lambda entry:entry[0])
            choice = int(random.integers(1,min(12,len(options))))
            loss,labels,angles = options[choice]
            if stale > 4:
                loss,labels,angles = best[0],best[1].copy(),best[2].copy()
                for mutation in range(2):
                    position = int(random.integers(len(labels)))
                    labels[position] = int(random.integers(len(model.labels)))
                    angles[position] = float(random.uniform(-1.3,1.3))
                loss,angles = model.fit(labels,angles,150)
                stale = 0
        print('ITER',iteration,'loss',loss,'best',best[0],'seconds',time.perf_counter()-started,flush=True)
        if loss<best[0]:
            best = loss,labels.copy(),angles.copy()
            write_candidate(case,model,labels,angles,loss)
        if best[0]<1e-12:
            break


if __name__ == '__main__':
    main()
