import copy
import json
from concurrent.futures import ProcessPoolExecutor

from cascade_sim import run_frame, validate_policy
from experiment import OUTPUT, load_suite, size
from learn_schedule import learn, leaves
from analyze_first import estimate


def choose_leaf(tree,features):
    while 'feature' in tree:
        tree=tree['left'] if features[tree['feature']]<=tree['threshold'] else tree['right']
    return tree['action']


def features_worker(payload):
    case,seed,policy=payload
    policy=copy.deepcopy(policy)
    policy['max_passes']=4
    policy['rules']=[]
    result=run_frame(case,seed,policy,trace=True)
    return seed,result['trace'][1]['features']


def install_separate(first_tree,second_tree,base,policies):
    policy=copy.deepcopy(base)
    rules=[]
    for conditions,name in leaves(first_tree):
        rules.append(dict(when=[['pass_index','le',0],['latency','le',.001],['frame_bits','ge',1024]]+conditions,
                          action=dict(size=policies[name]['schedule'][0]['size'])))
    for conditions,scale in leaves(second_tree):
        rules.append(dict(when=[['pass_index','ge',1],['pass_index','le',1],['latency','le',.001],['frame_bits','ge',1024]]+conditions,
                          action=dict(size=size('parity',scale))))
    policy['rules']=rules+policy['rules']
    validate_policy(policy)
    return policy


if __name__ == '__main__':
    policies=json.loads((OUTPUT/'bandwidth_grid_policies.json').read_text())
    records=json.loads((OUTPUT/'bandwidth_grid_records.json').read_text())
    first_tree=json.loads((OUTPUT/'learned_trees.json').read_text())['tree_depth2_min120']
    first_rows={}
    payloads=[]
    for split,frames in [('train',None),('dev',None),('independent',4)]:
        for case in load_suite(split,frames)['cases']:
            if case['family']!='bandwidth':
                continue
            for seed in case['frame_seeds']:
                features=dict(case,q_est=estimate(case,seed))
                features['q_se']=(features['q_est']*(1-features['q_est'])/(case['sample_size']+1))**.5
                name=choose_leaf(first_tree,features)
                first_rows[seed]=dict(case=case,name=name)
                payloads.append((case,seed,policies[name]))
    with ProcessPoolExecutor(max_workers=16) as executor:
        observed=dict(executor.map(features_worker,payloads))
    (OUTPUT/'first_pass_features.json').write_text(json.dumps(observed))
    lookups={name:{record['seed']:record for record in records[name]['bandwidth']} for name in policies}
    actions=[1.5,2,2.5,3,3.5,4,5,6]
    rows=[]
    for seed,features in observed.items():
        first=policies[first_rows[seed]['name']]['schedule'][0]['size']['scale']
        names=[f'first{first}_second{second}' for second in actions]
        if any(lookups[name][seed]['failure'] for name in names):
            continue
        row=dict(features,costs=[lookups[name][seed]['cost'] for name in names])
        rows.append(row)
    thresholds=dict(last_odd_fraction=[.1,.2,.3,.4,.45,.5,.55,.6],estimate_ratio=[.5,.75,1,1.25,1.5,2,3,4],
                    parity_est=[.004,.008,.016,.032,.064,.1],corrected_fraction=[.002,.004,.008,.016,.032,.064],
                    first_size=[8,16,32,64,128,256,512],frame_bits=[1024,2048],latency=[.0002,.0005])
    base=json.loads((OUTPUT/'inverse_dev_policies.json').read_text())['mixed1_third0.25_fast5_slow9_factor1.5']
    candidates={}
    trees={}
    for depth in [1,2,3]:
        for minimum in [100,160]:
            name=f'stage2_depth{depth}_min{minimum}'
            tree=learn(rows,actions,depth,minimum,thresholds)
            trees[name]=tree
            candidates[name]=install_separate(first_tree,tree,base,policies)
            print(name,json.dumps(tree),flush=True)
    (OUTPUT/'stage2_trees.json').write_text(json.dumps(trees,indent=2))
    (OUTPUT/'stage2_candidates.json').write_text(json.dumps(candidates,indent=2))
