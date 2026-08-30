import copy
import json
from experiment import OUTPUT,size


def short_frame_refinement(policy):
    refined=copy.deepcopy(policy)
    common=[['pass_index','le',0],['latency','ge',.003],['sample_size','le',256]]
    refined['rules']=[
        dict(when=common+[['frame_bits','ge',1024],['frame_bits','le',1024],['q_est','le',.006]],action=dict(size=size('frame',.125))),
        dict(when=common+[['frame_bits','ge',2048],['frame_bits','le',2048],['q_est','le',.003]],action=dict(size=size('frame',.125))),
        dict(when=common+[['frame_bits','ge',1024],['frame_bits','le',2048]],action=dict(size=size('estimate',.75))),
    ]+refined['rules']
    return refined


if __name__ == '__main__':
    base=json.loads((OUTPUT/'hierarchy_candidates.json').read_text())['hierarchy_mixed']
    candidates={'refined':short_frame_refinement(base)}
    safer=copy.deepcopy(candidates['refined'])
    for index,rule in enumerate(safer['rules']):
        if ['pass_index','ge',10] in rule['when'] and ['quiet_passes','lt',9] in rule['when']:
            conditions=rule['when']
            safer['rules'][index:index+1]=[
                dict(when=conditions+[['estimate_ratio','ge',.5]],action=rule['action']),
                dict(when=conditions+[['parity_est','ge',.008]],action=rule['action']),
                dict(when=[['pass_index','ge',11],['quiet_passes','ge',9],['quiet_passes','lt',10],['corrected_fraction','gt',0]],action=dict(stop=True)),
            ]
            break
    candidates['refined_safer']=safer
    (OUTPUT/'refined_candidates.json').write_text(json.dumps(candidates,indent=2))
