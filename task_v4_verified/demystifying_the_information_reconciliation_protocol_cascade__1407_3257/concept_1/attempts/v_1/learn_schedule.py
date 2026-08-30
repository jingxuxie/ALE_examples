import copy
import json
import math

from analyze_first import estimate
from experiment import OUTPUT, load_suite, size


def learn(rows, actions, depth, minimum, feature_thresholds=None):
    totals = [sum(row['costs'][index] for row in rows) for index in range(len(actions))]
    best = min(range(len(actions)),key=lambda index:totals[index])
    node = dict(action=actions[best],count=len(rows),cost=totals[best])
    if depth == 0 or len(rows)<minimum*2:
        return node
    best_split = None
    best_cost = totals[best] - .001*len(rows)
    thresholds = dict(frame_bits=[1024,2048],sample_size=[96,128,256,384,512],latency=[.0002,.0005],
                      q_est=[.003,.004,.006,.008,.012,.016,.024,.032,.048,.064,.08,.10],
                      q_se=[.002,.004,.006,.008,.012,.016,.024])
    if feature_thresholds is not None:
        thresholds=feature_thresholds
    for feature, values in thresholds.items():
        for threshold in values:
            left = [row for row in rows if row[feature]<=threshold]
            right = [row for row in rows if row[feature]>threshold]
            if min(len(left),len(right))<minimum:
                continue
            left_totals = [sum(row['costs'][index] for row in left) for index in range(len(actions))]
            right_totals = [totals[index]-left_totals[index] for index in range(len(actions))]
            loss = min(left_totals)+min(right_totals)
            if loss<best_cost:
                best_cost=loss
                best_split=feature,threshold,left,right
    if best_split is not None:
        feature,threshold,left,right=best_split
        node.update(feature=feature,threshold=threshold,
                    left=learn(left,actions,depth-1,minimum,thresholds),right=learn(right,actions,depth-1,minimum,thresholds))
    return node


def leaves(tree,conditions=None):
    conditions = [] if conditions is None else conditions
    if 'feature' not in tree:
        return [(conditions,tree['action'])]
    return (leaves(tree['left'],conditions+[[tree['feature'],'le',tree['threshold']]])+
            leaves(tree['right'],conditions+[[tree['feature'],'gt',tree['threshold']]]))


def install(tree,base,policies):
    policy=copy.deepcopy(base)
    rules=[]
    for conditions,name in leaves(tree):
        pair=policies[name]
        for pass_index in [0,1]:
            rules.append(dict(when=[['pass_index','ge',pass_index],['pass_index','le',pass_index],
                                    ['latency','le',.001],['frame_bits','ge',1024]]+conditions,
                              action=dict(size=pair['schedule'][pass_index]['size'])))
    policy['rules']=rules+policy['rules']
    return policy


if __name__ == '__main__':
    records=json.loads((OUTPUT/'bandwidth_grid_records.json').read_text())
    policies=json.loads((OUTPUT/'bandwidth_grid_policies.json').read_text())
    actions=list(policies)
    lookups={name:{record['seed']:record for record in records[name]['bandwidth']} for name in actions}
    rows=[]
    for split,frames in [('train',None),('dev',None),('independent',4)]:
        for case in load_suite(split,frames)['cases']:
            if case['family']!='bandwidth':
                continue
            for seed in case['frame_seeds']:
                row=dict(case)
                row['q_est']=estimate(case,seed)
                row['q_se']=math.sqrt(row['q_est']*(1-row['q_est'])/(case['sample_size']+1))
                if any(lookups[name][seed]['failure'] for name in actions):
                    continue
                row['costs']=[lookups[name][seed]['cost'] for name in actions]
                rows.append(row)
    trees={}
    candidates={}
    base=json.loads((OUTPUT/'inverse_dev_policies.json').read_text())['mixed1_third0.25_fast5_slow9_factor1.5']
    for depth in [0,1,2,3]:
        for minimum in ([120,180] if depth>0 else [120]):
            name=f'tree_depth{depth}_min{minimum}'
            tree=learn(rows,actions,depth,minimum)
            trees[name]=tree
            candidates[name]=install(tree,base,policies)
            print(name,len(rows),json.dumps(tree),flush=True)
    (OUTPUT/'learned_trees.json').write_text(json.dumps(trees,indent=2))
    (OUTPUT/'learned_candidates.json').write_text(json.dumps(candidates,indent=2))
