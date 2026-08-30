import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import argparse
import time
from concurrent.futures import ProcessPoolExecutor,as_completed

import numpy as np
from scipy.ndimage import label

from optimize import Model,OUTPUT


def samples(job):
    begin,count,prior=job
    model=Model()
    random=np.random.default_rng(begin+9988123123)
    features=[]
    labels=[]
    for index in range(count):
        while True:
            pattern=np.zeros(144,dtype=int)
            if prior is None:
                pattern[random.choice(144,54,replace=False)]=1
            else:
                logits=np.log(prior/(1-prior))+random.gumbel(size=144)
                pattern[np.argsort(logits)[-54:]]=1
            grid=np.ones((16,16),dtype=int)
            grid.ravel()[model.candidates]=1-pattern
            if label(grid)[1]==1:
                break
        objective,observed=model.evaluate(pattern,gradient=False)
        features.append(np.log(observed+.002).ravel().astype(np.float32))
        labels.append(pattern.astype(np.uint8))
    return begin,np.array(features),np.array(labels)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',type=int,default=24000)
    parser.add_argument('--workers',type=int,default=64)
    parser.add_argument('--epochs',type=int,default=160)
    parser.add_argument('--prior')
    parser.add_argument('--tag',default='learned')
    parser.add_argument('--pretrained')
    arguments=parser.parse_args()
    features=np.zeros((arguments.samples,2904),dtype=np.float32)
    labels=np.zeros((arguments.samples,144),dtype=np.uint8)
    start=time.time()
    prior=np.clip(np.load(arguments.prior),.05,.95) if arguments.prior else None
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures=[executor.submit(samples,(begin,min(50,arguments.samples-begin),prior)) for begin in range(0,arguments.samples,50)]
        completed=0
        for future in as_completed(futures):
            begin,chunk_features,chunk_labels=future.result()
            features[begin:begin+len(chunk_features)]=chunk_features
            labels[begin:begin+len(chunk_labels)]=chunk_labels
            completed+=len(chunk_features)
            if completed%1000==0:
                print('DATA',completed,'elapsed',time.time()-start,flush=True)
    np.savez(OUTPUT/f'{arguments.tag}_training.npz',features=features,labels=labels)
    import torch
    torch.set_num_threads(12)
    torch.manual_seed(51)
    mean=features.mean(axis=0,keepdims=True)
    scale=features.std(axis=0,keepdims=True)+.01
    checkpoint=None
    if arguments.pretrained:
        checkpoint=torch.load(arguments.pretrained,weights_only=False)
        mean,scale=checkpoint['mean'],checkpoint['scale']
    features=(features-mean)/scale
    feature_tensor=torch.tensor(features)
    label_tensor=torch.tensor(labels,dtype=torch.float32)
    model=Model()
    target_tensor=torch.tensor((np.log(model.target+.002).ravel()[None].astype(np.float32)-mean)/scale)
    network=torch.nn.Sequential(torch.nn.Linear(2904,1024),torch.nn.LayerNorm(1024),torch.nn.GELU(),torch.nn.Dropout(.1),torch.nn.Linear(1024,512),torch.nn.LayerNorm(512),torch.nn.GELU(),torch.nn.Dropout(.1),torch.nn.Linear(512,256),torch.nn.GELU(),torch.nn.Linear(256,144))
    if checkpoint is not None:
        network.load_state_dict(checkpoint['state'])
    optimizer=torch.optim.AdamW(network.parameters(),lr=.0003 if checkpoint is not None else .001,weight_decay=.003)
    validation=2000
    best=1e9
    for epoch in range(arguments.epochs):
        network.train()
        order=torch.randperm(arguments.samples-validation)+validation
        losses=[]
        for batch in order.split(512):
            optimizer.zero_grad(set_to_none=True)
            logits=network(feature_tensor[batch])
            loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,label_tensor[batch])
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        network.eval()
        with torch.no_grad():
            logits=network(feature_tensor[:validation])
            validation_loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,label_tensor[:validation]).item()
            prediction=network(target_tensor).sigmoid()[0].numpy()
            indices=logits.topk(54,dim=1).indices
            hard=torch.zeros_like(logits).scatter_(1,indices,1)
            accuracy=(hard==label_tensor[:validation]).float().mean().item()
        print('EPOCH',epoch,'elapsed',time.time()-start,'train',np.mean(losses),'valid',validation_loss,'accuracy',accuracy,flush=True)
        if validation_loss<best:
            best=validation_loss
            np.save(OUTPUT/f'{arguments.tag}_prediction.npy',prediction)
            torch.save({'state':network.state_dict(),'mean':mean,'scale':scale},OUTPUT/f'{arguments.tag}_model.pt')
        if epoch%40==39:
            for group in optimizer.param_groups:
                group['lr']*=.5
