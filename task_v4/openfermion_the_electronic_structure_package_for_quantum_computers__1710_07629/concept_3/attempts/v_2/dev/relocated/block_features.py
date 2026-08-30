from functools import lru_cache
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
from scipy.linalg import eigh
from active_features import operators
from native_eigh import lowest,add_link,dense_lowest,block_matrix

@lru_cache(None)
def masks_for(sites,particles):
    return np.array([mask for mask in range(1<<sites) if mask.bit_count()==particles])

@lru_cache(None)
def occupations(sites,particles):
    return ((masks_for(sites,particles)[None,:]>>np.arange(sites)[:,None])&1).astype(float)

@lru_cache(None)
def creation(sites,particles,site):
    before=masks_for(sites,particles)
    after=masks_for(sites,particles+1)
    lookup={mask:index for index,mask in enumerate(after)}
    matrix=np.zeros((len(after),len(before)))
    for column,mask in enumerate(before):
        if (mask>>site)&1:
            continue
        matrix[lookup[mask|(1<<site)],column]=(-1)**(int(mask&((1<<site)-1)).bit_count())
    return matrix

@lru_cache(None)
def partitions(sites):
    size=sites//2 if sites==12 else 4
    masks=masks_for(sites,size)
    if size*2==sites:
        masks=masks[(masks&1)!=0]
    return ((masks[:,None]>>np.arange(sites)[None,:])&1).astype(float)

def divide(hopping):
    choices=partitions(len(hopping))
    costs=np.sum((choices@hopping**2)*(1-choices),axis=1)
    selected=choices[np.argmin(costs)]>0
    return np.flatnonzero(selected),np.flatnonzero(~selected),float(np.min(costs))

class Block:
    def __init__(self,hopping,interaction,potential,maximum):
        self.sites=len(interaction)
        self.states={}
        self.transforms={}
        reached={0}
        pending=[0]
        while pending:
            site=pending.pop()
            for neighbor in np.flatnonzero(hopping[site]):
                if int(neighbor) not in reached:
                    reached.add(int(neighbor))
                    pending.append(int(neighbor))
        if len(reached)<self.sites:
            maximum=max(maximum,10)
        for up in range(self.sites+1):
            for down in range(self.sites+1):
                if abs(up+down-self.sites)>2 or abs(up-down)>3:
                    continue
                if down<up:
                    continue
                dimension_up=len(masks_for(self.sites,up))
                dimension_down=len(masks_for(self.sites,down))
                matrix=block_matrix(hopping,interaction,potential,up,down,dimension_up*dimension_down)
                number=min(maximum,len(matrix))
                values,vectors=lowest(matrix,number,1e-7)
                vectors=vectors.reshape(dimension_up,dimension_down,number)
                self.states[up,down]=(values,vectors)
                if up!=down:
                    self.states[down,up]=(values,vectors.transpose(1,0,2).copy())

    def transform(self,sector,spin,site):
        key=(sector,spin,site)
        if key in self.transforms:
            return self.transforms[key]
        up,down=sector
        target=(up+1,down) if spin==0 else (up,down+1)
        if target not in self.states:
            return None
        source_vectors=self.states[sector][1]
        target_vectors=self.states[target][1]
        if spin==0:
            operator=creation(self.sites,up,site)
            rows,columns=np.where(operator)
            transformed=np.zeros((len(operator),source_vectors.shape[1],source_vectors.shape[2]))
            transformed[rows,:,:]=operator[rows,columns,None,None]*source_vectors[columns,:,:]
        else:
            operator=creation(self.sites,down,site)*(-1)**up
            rows,columns=np.where(operator)
            transformed=np.zeros((source_vectors.shape[0],len(operator),source_vectors.shape[2]))
            transformed[:,rows,:]=operator[rows,columns,None]*source_vectors[:,columns,:]
        overlap=target_vectors.reshape(-1,target_vectors.shape[-1]).T@transformed.reshape(-1,transformed.shape[-1])
        self.transforms[key]=overlap
        return overlap

def combined(first,second,cross,up,down,retained,perturb=False):
    offsets={}
    sizes={}
    dimension=0
    for sector in first.states:
        other=(up-sector[0],down-sector[1])
        if other not in second.states:
            continue
        energies_first=first.states[sector][0]
        energies_second=second.states[other][0]
        size_first=min(len(energies_first),retained)
        size_second=min(len(energies_second),retained)
        while size_first<len(energies_first) and energies_first[size_first]-energies_first[size_first-1]<1e-7:
            size_first+=1
        while size_second<len(energies_second) and energies_second[size_second]-energies_second[size_second-1]<1e-7:
            size_second+=1
        offsets[sector]=dimension
        sizes[sector]=(size_first,size_second)
        dimension+=size_first*size_second
    matrix=np.zeros((dimension,dimension))
    for sector,offset in offsets.items():
        size_first,size_second=sizes[sector]
        other=(up-sector[0],down-sector[1])
        energies=(first.states[sector][0][:size_first,None]+second.states[other][0][None,:size_second]).ravel()
        indices=offset+np.arange(len(energies))
        matrix[indices,indices]=energies
        for spin in range(2):
            next_sector=(sector[0]+(spin==0),sector[1]+(spin==1))
            if next_sector not in offsets:
                continue
            next_other=(other[0]-(spin==0),other[1]-(spin==1))
            next_first,next_second=sizes[next_sector]
            for site_first,site_second in zip(*np.where(cross!=0)):
                left=first.transform(sector,spin,int(site_first))[:next_first,:size_first]
                right=second.transform(next_other,spin,int(site_second))[:size_second,:next_second].T
                add_link(matrix,offset,offsets[next_sector],-cross[site_first,site_second]*(-1)**sum(sector),left,right)
    values,vectors=lowest(matrix,1,1e-6)
    energy=values[0]
    if not perturb:
        return energy
    wavefunctions={}
    residuals={}
    for sector,offset in offsets.items():
        size_first,size_second=sizes[sector]
        other=(up-sector[0],down-sector[1])
        wavefunctions[sector]=vectors[offset:offset+size_first*size_second,0].reshape(size_first,size_second)
        residuals[sector]=np.zeros((len(first.states[sector][0]),len(second.states[other][0])))
    for sector in offsets:
        other=(up-sector[0],down-sector[1])
        size_first,size_second=sizes[sector]
        for spin in range(2):
            next_sector=(sector[0]+(spin==0),sector[1]+(spin==1))
            if next_sector not in offsets:
                continue
            next_other=(other[0]-(spin==0),other[1]-(spin==1))
            next_first,next_second=sizes[next_sector]
            for site_first,site_second in zip(*np.where(cross!=0)):
                left=first.transform(sector,spin,int(site_first))
                right=second.transform(next_other,spin,int(site_second)).T
                strength=-cross[site_first,site_second]*(-1)**sum(sector)
                residuals[next_sector]+=strength*(left[:,:size_first]@wavefunctions[sector]@right[:,:size_second].T)
                residuals[sector]+=strength*(left[:next_first,:].T@wavefunctions[next_sector]@right[:next_second,:])
    weights=[]
    denominators=[]
    for sector in offsets:
        other=(up-sector[0],down-sector[1])
        size_first,size_second=sizes[sector]
        residuals[sector][:size_first,:size_second]=0
        weights.extend((residuals[sector]**2).ravel())
        denominators.extend((first.states[sector][0][:,None]+second.states[other][0][None,:]-energy).ravel())
    weights=np.asarray(weights)
    denominators=np.maximum(np.asarray(denominators),1e-8)
    correction=-np.sum(weights/denominators)
    lower,upper=correction,0.
    for iteration in range(35):
        middle=(lower+upper)/2
        if middle+np.sum(weights/(denominators-middle))>0:
            upper=middle
        else:
            lower=middle
    shifted=(lower+upper)/2
    return energy,energy+correction,energy+shifted,np.sum(weights/(denominators-shifted)**2)

def calculate(hopping,interaction,potential,counts=(4,8)):
    sites=len(interaction)
    half=sites//2
    left,right,cost=divide(hopping)
    first=Block(hopping[np.ix_(left,left)],interaction[left],potential[left],max(counts))
    second=Block(hopping[np.ix_(right,right)],interaction[right],potential[right],max(counts))
    cross=hopping[np.ix_(left,right)]
    result=[cost]
    for retained in counts:
        neutral=combined(first,second,cross,half,half,retained)
        spin=combined(first,second,cross,half+1,half-1,retained)
        removed=combined(first,second,cross,half,half-1,retained)
        added=combined(first,second,cross,half+1,half,retained)
        result.extend([added+removed-2*neutral,spin-neutral,neutral,added-neutral,neutral-removed])
    return result

def features(inputs):
    return np.asarray([calculate(inputs['hopping'][index,:sites,:sites],inputs['interaction'][index,:sites],inputs['potential'][index,:sites]) for index,sites in enumerate(inputs['n_sites'])])

def calculate_perturb(hopping,interaction,potential):
    sites=len(interaction)
    half=sites//2
    left,right,cost=divide(hopping)
    first=Block(hopping[np.ix_(left,left)],interaction[left],potential[left],8)
    second=Block(hopping[np.ix_(right,right)],interaction[right],potential[right],8)
    cross=hopping[np.ix_(left,right)]
    energies=np.asarray([combined(first,second,cross,up,down,4,perturb=True) for up,down in [(half,half),(half+1,half-1),(half,half-1),(half+1,half)]])
    result=[cost]
    for column in range(3):
        neutral,spin,removed,added=energies[:,column]
        result.extend([added+removed-2*neutral,spin-neutral,neutral,added-neutral,neutral-removed])
    result.extend(energies[:,3])
    return result
