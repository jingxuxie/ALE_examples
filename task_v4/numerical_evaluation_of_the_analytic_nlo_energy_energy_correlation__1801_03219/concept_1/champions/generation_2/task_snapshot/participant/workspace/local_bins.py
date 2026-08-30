import numpy as np
from numpy.polynomial import chebyshev,legendre


NODES,WEIGHTS = legendre.leggauss(40)


def bin_average_local(model,lower,upper,endpoint_base=None):
    if not -24 <= lower < upper <= 24:
        raise ValueError("invalid physical bin")
    total = np.zeros(3)
    charts = model.get("charts",["density"]*(len(model["knots"])-1))
    for interval,(left,right,chart) in enumerate(zip(model["knots"][:-1],model["knots"][1:],charts)):
        first,last = max(lower,left),min(upper,right)
        if last <= first:
            continue
        subknots = np.linspace(first,last,int(np.ceil((last-first)/2))+1)
        for start,stop in zip(subknots[:-1],subknots[1:]):
            fractions = (NODES+1)/2
            local = 2*((start-left)+(stop-start)*fractions)/(right-left)-1
            latent = np.array([chebyshev.chebval(local,coefficients) for coefficients in model["coefficients"][interval]]).T
            if chart == "density":
                values = latent
            else:
                if endpoint_base is None:
                    raise ValueError("residual charts require their endpoint base")
                coordinates = start+(stop-start)*fractions
                base,unused_derivative = endpoint_base(coordinates,chart)
                scale = 1/((1+np.exp(-coordinates))*(1+np.exp(coordinates)))
                values = base+scale[:,None]*latent
            total += ((stop-start)/(upper-lower))*(WEIGHTS @ values)/2
    return total
