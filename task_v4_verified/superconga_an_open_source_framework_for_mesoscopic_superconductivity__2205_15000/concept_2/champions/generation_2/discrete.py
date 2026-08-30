from optimize import *


class SwapModel(Model):
    def __init__(self, stride=3, conditions=1):
        config = dict(CONFIG)
        config['energies'] = CONFIG['energies'][::stride]
        config['conditions'] = CONFIG['conditions'][:conditions]
        super().__init__(config, TARGET[:conditions, :, ::stride])
        self.neighbors = self.neighbor_sites[:,1].reshape(64,8)

    def all_swaps(self, pattern, chunk=32):
        occupied, empty = np.nonzero(pattern)[0], np.nonzero(1-pattern)[0]
        removed = np.repeat(occupied, len(empty))
        added = np.tile(empty, len(occupied))
        moves = np.stack([removed, added], axis=1)
        losses = np.zeros(len(moves))
        spectral_norm = self.target.size
        for condition_index in range(len(self.base)):
            matrix, amplitude = self.matrix(pattern, condition_index)
            eigenvalues, vectors = eigh(matrix, check_finite=False, driver='evr')
            factors = 1/(self.energies[:,None] + 1j*self.eta - eigenvalues[None,:])
            green = (vectors[None,:,:] * factors[:,None,:]) @ vectors.conj().T
            observed = -green[:, self.probes, self.probes].imag/np.pi
            for start in range(0,len(moves),chunk):
                batch = moves[start:start+chunk]
                sites = self.candidates[batch]
                selected = np.concatenate([sites, sites+self.sites], axis=1)
                local = self.neighbors[batch]
                indices = np.concatenate([np.concatenate([sites[:,:,None], local+self.sites],axis=2), np.concatenate([sites[:,:,None]+self.sites,local],axis=2)],axis=1)
                delta = np.array([-1.,1.])[None,:,None]
                new_amplitudes = np.broadcast_to(amplitude[None,None,:], (len(batch),2,self.sites)).copy()
                new_amplitudes[np.arange(len(batch))[:,None,None],np.arange(2)[None,:,None],sites[:,None,:]] = np.array([1.,0.])[None,None,:]
                neighbor_new = np.take_along_axis(new_amplitudes, local, axis=2)
                change = np.array([1.,0.])[None,:,None]*neighbor_new - amplitude[sites][:,:,None]*amplitude[local]
                pairvalues = self.pairing[condition_index,sites[:,:,None],local] * change
                values = np.concatenate([np.concatenate([np.broadcast_to(6*delta,(len(batch),2,1)), pairvalues.conj()],axis=2),np.concatenate([np.broadcast_to(-6*delta,(len(batch),2,1)),pairvalues],axis=2)],axis=1)
                values *= np.where(np.any(indices[:,:,:,None] == selected[:,None,None,:],axis=-1), .5, 1)
                gee = green[:, selected[:,:,None], selected[:,None,:]].transpose(1,0,2,3)
                gea = np.sum(green[:,selected[:,:,None,None],indices[:,None,:,:]].transpose(1,0,2,3,4)*values[:,None,None,:,:],axis=-1)
                gae = np.sum(green[:,indices[:,:,:,None],selected[:,None,None,:]].transpose(1,0,2,3,4)*values.conj()[:,None,:,:,None],axis=-2)
                gaa = np.einsum('meirjs,mir,mjs->meij',green[:,indices[:,:,:,None,None],indices[:,None,None,:,:]].transpose(1,0,2,3,4,5),values.conj(),values,optimize=True)
                interaction = np.concatenate([np.concatenate([gea,gee],axis=-1),np.concatenate([gaa,gae],axis=-1)],axis=-2)
                gpe = green[:,self.probes[None,:,None],selected[:,None,:]].transpose(1,0,2,3)
                gep = green[:,selected[:,:,None],self.probes[None,None,:]].transpose(1,0,2,3)
                gpa = np.sum(green[:,self.probes[None,:,None,None],indices[:,None,:,:]].transpose(1,0,2,3,4)*values[:,None,None,:,:],axis=-1)
                gap = np.sum(green[:,indices[:,:,:,None],self.probes[None,None,None,:]].transpose(1,0,2,3,4)*values.conj()[:,None,:,:,None],axis=-2)
                right = np.concatenate([gep,gap],axis=-2)
                left = np.concatenate([gpa,gpe],axis=-1)
                solved = np.linalg.solve(np.eye(8)-interaction,right)
                correction = np.einsum('mepi,meip->mep',left,solved,optimize=True)
                spectra = observed[None,:,:] - correction.imag/np.pi
                residual = (spectra.transpose(0,2,1)-self.target[condition_index])/self.scale[condition_index]
                losses[start:start+len(batch)] += np.sum(residual**2,axis=(1,2))/spectral_norm
        return moves,losses


def check():
    model=SwapModel()
    random=np.random.default_rng(90)
    pattern=np.zeros(64,dtype=int)
    pattern[random.choice(64,24,False)]=1
    start=time.monotonic()
    moves,losses=model.all_swaps(pattern)
    print('all swaps',time.monotonic()-start, 'best',losses.min())
    for index in [0,123,450,959]:
        candidate=pattern.copy()
        candidate[moves[index,0]]=0
        candidate[moves[index,1]]=1
        loss=model.evaluate(candidate,False)[0]
        print(index,losses[index],loss,losses[index]-loss)


if __name__=='__main__':
    check()
