import copy
import json
from experiment import OUTPUT, size


def hierarchy(mixed=False,mid=8,ratio=.75,late=True,low=9,slow=10):
    base=json.loads((OUTPUT/'stage2_candidates.json').read_text())['stage2_depth2_min100']
    rules=[]
    for frame_bits in [512,1024,2048,4096,8192]:
        common=[['pass_index','ge',3],['frame_bits','ge',frame_bits],['frame_bits','le',frame_bits],['corrected_fraction','le',2/frame_bits]]
        rules.append(dict(when=common+[['quiet_passes','lt',low]],action=dict(stop=False)))
        rules.append(dict(when=common+[['quiet_passes','ge',low],['corrected_fraction','gt',0]],action=dict(stop=True)))
    if late:
        rules.append(dict(when=[['pass_index','ge',7],['quiet_passes','ge',3],['quiet_passes','lt',4],['corrected_fraction','gt',0]],action=dict(stop=True)))
    rules.extend([
        dict(when=[['pass_index','ge',7],['quiet_passes','ge',4],['quiet_passes','lt',5],['estimate_ratio','ge',ratio],['latency','le',.001],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',8],['quiet_passes','ge',5],['quiet_passes','lt',6],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',mid+2],['quiet_passes','ge',mid],['quiet_passes','lt',mid+1],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',slow],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',14]],action=dict(stop=True)),
    ])
    if mixed:
        rules.append(dict(when=[['pass_index','le',0],['frame_bits','ge',4096],['q_est','ge',.03],['latency','le',.001]],action=dict(size=size('estimate',1))))
    rules.extend(rule for rule in base['rules'] if 'stop' not in rule['action'])
    base['rules']=rules
    return base


if __name__ == '__main__':
    candidates={
        'hierarchy':hierarchy(),
        'hierarchy_mixed':hierarchy(mixed=True),
        'hierarchy_ratio1.5':hierarchy(ratio=1.5),
        'hierarchy_mid9':hierarchy(mid=9),
        'hierarchy_no_late':hierarchy(late=False),
        'hierarchy_slow11':hierarchy(slow=11),
    }
    (OUTPUT/'hierarchy_candidates.json').write_text(json.dumps(candidates,indent=2))
