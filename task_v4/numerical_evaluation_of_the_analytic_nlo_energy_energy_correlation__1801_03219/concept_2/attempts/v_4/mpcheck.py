from design import *
import mpmath as mp
import bisect


def reference(witness,order,panels,precision):
    mp.mp.dps=precision
    lower_float,upper_float=BINS[witness['bin']]
    lower,upper=mp.mpf(lower_float),mp.mpf(upper_float)
    edges=[mp.mpf(float(edge)) for edge in kernel.edges]
    coefficients=[[[mp.mpf(float(value)) for value in channel] for channel in segment] for segment in kernel.coefficients]
    colors=[mp.mpf(float(value)) for value in COLOR]
    fourier=[mp.mpf(value)/10**10 for value in witness['cosine']+witness['sine']]
    frequencies=list(range(witness['band_start'],witness['band_start']+12))
    nodes,weights=mp.gauss_quadrature(order,'legendre')
    boundaries=[mp.mpf(index)/panels for index in range(panels+1)]
    boundaries.extend((edge-lower)/(upper-lower) for edge in edges if lower<edge<upper)
    boundaries=sorted(set(boundaries))
    totals=[mp.mpf(0) for family in FAMILIES]
    absolute=[mp.mpf(0) for family in FAMILIES]
    for start,end in zip(boundaries[:-1],boundaries[1:]):
        middle=(start+end)/2
        half=(end-start)/2
        index=bisect.bisect_right(edges,lower+(upper-lower)*middle)-1
        for node,quadrature_weight in zip(nodes,weights):
            point=middle+half*node
            position=lower+(upper-lower)*point
            coordinate=(2*position-edges[index]-edges[index+1])/(edges[index+1]-edges[index])
            waveform=mp.fsum(fourier[mode]*mp.cos(2*mp.pi*frequency*point)+fourier[12+mode]*mp.sin(2*mp.pi*frequency*point) for mode,frequency in enumerate(frequencies))
            shifted=2*point-1
            detector=(1+mp.mpf(witness['tilt'])/16*shifted+mp.mpf(witness['curvature'])/16*(shifted**2-mp.mpf(1)/3))/mp.mpf('1.5')
            factor=2*(upper-lower)*detector*waveform*half*quadrature_weight
            for family in range(3):
                previous=mp.mpf(0)
                current=mp.mpf(0)
                for coefficient in coefficients[index][family][:0:-1]:
                    previous,current=current,coefficient+2*coordinate*current-previous
                value=coefficients[index][family][0]+coordinate*current-previous
                contribution=factor*colors[family]*value
                totals[family]+=contribution
                absolute[family]+=abs(contribution)
    return totals,absolute


if __name__=='__main__':
    witness=json.loads(Path('witness.json').read_text())
    coarse,coarse_absolute=reference(witness,24,32,50)
    print('COARSE',[mp.nstr(value,45) for value in coarse],flush=True)
    fine,fine_absolute=reference(witness,36,64,80)
    print('FINE',[mp.nstr(value,65) for value in fine],flush=True)
    print('GAPS',[mp.nstr(abs(first-second),15) for first,second in zip(coarse,fine)],flush=True)
    print('L1',[mp.nstr(max(first,second)+4*abs(first-second),30) for first,second in zip(coarse_absolute,fine_absolute)],flush=True)
