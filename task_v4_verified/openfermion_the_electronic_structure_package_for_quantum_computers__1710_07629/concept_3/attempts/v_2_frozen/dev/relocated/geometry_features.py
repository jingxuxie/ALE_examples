from functools import lru_cache
import numpy as np

@lru_cache(None)
def template(sites,family):
    adjacency=np.zeros((sites,sites),dtype=bool)
    groups=[[],[],[],[]]
    def edge(first,second,group):
        adjacency[first,second]=adjacency[second,first]=True
        groups[group].append((first,second))
    if family==0:
        for site in range(sites):
            edge(site,(site+1)%sites,site%2)
    else:
        length=sites//2
        for leg in range(2):
            for column in range(length if family==3 else length-1):
                edge(leg*length+column,leg*length+(column+1)%length,column%2)
        for column in range(length):
            edge(column,length+column,2)
        if family==2:
            for column in range(length-1):
                edge(column,length+column+1,3)
    return adjacency,groups

def mapping(adjacency,reference):
    sites=len(adjacency)
    degree=adjacency.sum(1)
    refdegree=reference.sum(1)
    order=[]
    while len(order)<sites:
        remaining=[site for site in range(sites) if site not in order]
        order.append(max(remaining,key=lambda site:(reference[site,order].sum(),refdegree[site])))
    assignment=np.full(sites,-1,dtype=int)
    used=np.zeros(sites,dtype=bool)
    def search(position):
        if position==sites:
            return True
        site=order[position]
        earlier=order[:position]
        for candidate in np.flatnonzero((degree==refdegree[site])&~used):
            if not np.array_equal(adjacency[candidate,assignment[earlier]],reference[site,earlier]):
                continue
            assignment[site]=candidate
            used[candidate]=True
            if search(position+1):
                return True
            used[candidate]=False
        return False
    if not search(0):
        raise ValueError('Unrecognized graph')
    return assignment

def calculate(hopping,interaction,potential,family):
    sites=len(interaction)
    reference,groups=template(sites,int(family))
    permutation=mapping(hopping!=0,reference)
    hopping=hopping[np.ix_(permutation,permutation)]
    interaction=interaction[permutation]
    potential=potential[permutation]
    effective=potential+(interaction-interaction.mean())/2
    summaries=[]
    for edges in groups:
        if not edges:
            summaries.append(np.zeros(5))
            continue
        first,second=np.array(edges).T
        strengths=hopping[first,second]
        summaries.append(np.array([strengths.mean(),strengths.std(),np.mean((effective[first]-effective[second])**2),np.mean((effective[first]+effective[second])**2),np.mean((interaction[first]-interaction[second])**2)]))
    if summaries[0][0]<summaries[1][0]:
        summaries[0],summaries[1]=summaries[1],summaries[0]
    result=np.concatenate(summaries).tolist()
    result.extend([np.mean(interaction),np.std(interaction),np.std(effective),np.mean(effective**3),np.mean(effective**4),np.mean(potential*interaction)])
    return result

def features(inputs):
    return np.array([calculate(inputs['hopping'][index,:sites,:sites],inputs['interaction'][index,:sites],inputs['potential'][index,:sites],inputs['family'][index]) for index,sites in enumerate(inputs['n_sites'])])
