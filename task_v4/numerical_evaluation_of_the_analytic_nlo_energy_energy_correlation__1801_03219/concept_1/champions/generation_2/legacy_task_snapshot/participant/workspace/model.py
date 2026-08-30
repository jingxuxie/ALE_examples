import json
from pathlib import Path

import numpy as np
from numpy.polynomial import legendre, polynomial

from polynomial import evaluate as evaluate_polynomial
from polynomial import load_model as load_polynomial


TERMS = json.loads((Path(__file__).resolve().parents[1]/"input/endpoint_terms.json").read_text())
TERMS = {chart: [np.asarray(values,dtype=float) for values in channels] for chart,channels in TERMS.items()}
QUADRATURE_NODES,QUADRATURE_WEIGHTS = legendre.leggauss(40)


def load_model(path,enforce_budget=True):
    model = load_polynomial(path,enforce_budget=False)
    artifact = json.loads(Path(path).read_text())
    charts = artifact.get("charts",["density"]*(len(model["knots"])-1))
    if not isinstance(charts,list) or len(charts) != len(model["knots"])-1:
        raise ValueError("one chart string per interval required")
    for chart,left,right in zip(charts,model["knots"][:-1],model["knots"][1:]):
        if chart not in ["density","collinear","backward"]:
            raise ValueError("invalid chart")
        if chart == "collinear" and right > -4:
            raise ValueError("collinear chart must lie at t <= -4")
        if chart == "backward" and left < 4:
            raise ValueError("backward chart must lie at t >= 4")
    if enforce_budget and model["scalar_count"] > 268:
        raise ValueError(f"deployment uses {model['scalar_count']} scalars; maximum 268")
    model["charts"] = charts
    return model


def geometry(coordinates):
    angular = 1/(1+np.exp(-coordinates))
    complement = 1/(1+np.exp(coordinates))
    scale = angular*complement
    return angular,complement,scale,scale*(1-2*angular)


def endpoint_base(coordinates,chart):
    angular,complement,scale,scale_derivative = geometry(coordinates)
    logarithm = -np.log1p(np.exp(-coordinates if chart == "collinear" else coordinates))
    values = np.array([polynomial.polyval(logarithm,coefficients) for coefficients in TERMS[chart]]).T
    slopes = np.array([polynomial.polyval(logarithm,polynomial.polyder(coefficients)) for coefficients in TERMS[chart]]).T
    if chart == "collinear":
        base = complement[:,None]*values
        derivative = -scale[:,None]*values+complement[:,None]**2*slopes
    else:
        base = angular[:,None]*values
        derivative = scale[:,None]*values-angular[:,None]**2*slopes
    return base,derivative


def evaluate(model,coordinates,derivative=False,observable="residual"):
    coordinates = np.asarray(coordinates,dtype=float)
    flat = coordinates.reshape(-1)
    latent = evaluate_polynomial(model,flat)
    latent_derivative = evaluate_polynomial(model,flat,True) if derivative else np.zeros_like(latent)
    intervals = np.clip(np.searchsorted(model["knots"],flat,side="right")-1,0,len(model["knots"])-2)
    charts = np.asarray(model.get("charts",["density"]*(len(model["knots"])-1)))[intervals]
    angular,complement,scale,scale_derivative = geometry(flat)
    density,density_derivative = latent.copy(),latent_derivative.copy()
    for chart in ["collinear","backward"]:
        selected = charts == chart
        if np.any(selected):
            base,base_derivative = endpoint_base(flat[selected],chart)
            density[selected] = base+scale[selected,None]*latent[selected]
            density_derivative[selected] = base_derivative+scale_derivative[selected,None]*latent[selected]+scale[selected,None]*latent_derivative[selected]
    if observable == "density":
        result = density_derivative if derivative else density
    elif observable == "residual":
        result = density_derivative.copy() if derivative else density.copy()
        for chart,selected in [("collinear",flat < -4),("backward",flat >= 4)]:
            direct = selected & (charts == chart)
            result[direct] = latent_derivative[direct] if derivative else latent[direct]
            convert = selected & ~direct
            if np.any(convert):
                base,base_derivative = endpoint_base(flat[convert],chart)
                remainder = (density[convert]-base)/scale[convert,None]
                result[convert] = (density_derivative[convert]-base_derivative-scale_derivative[convert,None]*remainder)/scale[convert,None] if derivative else remainder
    else:
        raise ValueError("observable must be density or residual")
    return result.reshape(coordinates.shape+(3,))


def bin_average(model,lower,upper):
    if not -24 <= lower < upper <= 24:
        raise ValueError("invalid physical bin")
    knots = np.asarray(model["knots"])
    boundaries = np.unique(np.concatenate(([lower,upper],knots[(knots > lower)&(knots < upper)])))
    total = np.zeros(3)
    for left,right in zip(boundaries[:-1],boundaries[1:]):
        subknots = np.linspace(left,right,int(np.ceil((right-left)/2))+1)
        for start,stop in zip(subknots[:-1],subknots[1:]):
            coordinates = start+(stop-start)*(QUADRATURE_NODES+1)/2
            values = evaluate(model,coordinates,observable="density")
            total += ((stop-start)/(upper-lower))*(QUADRATURE_WEIGHTS @ values)/2
    return total
