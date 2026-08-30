import numpy as np

OMEGA = np.arange(-7.96875, 8, 0.0625)


def normalize(profile, derivative):
    total = profile.sum()
    mass = profile / total
    return mass, (derivative - mass[:, None] * derivative.sum(axis=0)) / total


def gaussian(center, width):
    delta = OMEGA - center
    profile = np.exp(-0.5 * (delta / width) ** 2)
    derivative = profile[:, None] * np.stack((delta / width**2, delta**2 / width**3), axis=1)
    return normalize(profile, derivative)


def continuum(center, width, skew, shape):
    scaled = (OMEGA - center) / width
    inside = np.abs(scaled) < 1
    base = np.maximum(1 - scaled**2, 1e-100)
    profile = np.where(inside, base**shape * np.exp(skew * np.clip(scaled, -1, 1)), 0)
    factor = np.where(inside, 1 / base, 0)
    derivative = profile[:, None] * np.stack((
        (2 * shape * scaled * factor - skew) / width,
        (2 * shape * scaled**2 * factor - skew * scaled) / width,
        scaled, np.log(base)), axis=1)
    return normalize(profile, derivative)


BOUNDS = [
    ([-.4, .09, .4, -.8, 2, -1.2, .3], [.4, .24, .85, .8, 4, 1.2, 1.8]),
    ([1.6, -.65, .4, .4, .25, .1, -.25, .09], [4.6, .65, 1, 1, .75, .45, .25, .26]),
    ([1.6, -.65, .4, .4, .25, 0, .1], [4.6, .65, 1, 1, .75, 1, .35]),
    ([-.6, 2, -1.4, .2, -.12, .25, .6, .6, .2, 0], [.6, 4.5, 1.4, 1.6, .12, 1, .98, 1.5, .5, .25]),
    ([-1.2, 2.2, -2, .2, 1.5, .25, .08], [1.2, 4.8, 2, 1.8, 4.8, .9, .4]),
]
BOUNDS = [(np.array(lower), np.array(upper) - np.array(lower)) for lower, upper in BOUNDS]
MODELS = [(0, 1), (1, 1), (2, 1), (3, -1), (3, 1), (4, -1), (4, 1)]


def spectrum(parameters, model):
    family, sign = MODELS[model]
    lower, scale = BOUNDS[family]
    values = lower + scale * parameters
    derivative = np.zeros((256, len(parameters)))
    if family == 0:
        center, width, weight, bgcenter, bgwidth, skew, shape = values
        peak, peakjac = gaussian(center, width)
        background, bgjac = continuum(bgcenter, bgwidth, skew, shape)
        mass = weight * peak + (1 - weight) * background
        derivative[:, :2] = weight * peakjac
        derivative[:, 2] = peak - background
        derivative[:, 3:] = (1 - weight) * bgjac
    elif family in (1, 2):
        separation, shift, leftwidth, rightwidth, leftweight = values[:5]
        left, leftjac = gaussian(shift - separation / 2, leftwidth)
        right, rightjac = gaussian(shift + separation / 2, rightwidth)
        if family == 2:
            gapunit, ramp = values[5:]
            gaprange = min(1.3, separation / 2 - .1) - .25
            gap = .25 + gapunit * gaprange
            rampcoord = (np.abs(OMEGA) - gap) / ramp
            suppression = np.clip(rampcoord, 0, 1)
            transition = ((rampcoord > 0) & (rampcoord < 1)).astype(float)
            supjac = np.stack((-transition.astype(float) / ramp, -transition * rampcoord / ramp), axis=1)
            left, leftjac = normalize(left * suppression, np.column_stack((leftjac * suppression[:, None], left[:, None] * supjac)))
            right, rightjac = normalize(right * suppression, np.column_stack((rightjac * suppression[:, None], right[:, None] * supjac)))
        mass = leftweight * left + (1 - leftweight) * right
        derivative[:, 0] = -.5 * leftweight * leftjac[:, 0] + .5 * (1 - leftweight) * rightjac[:, 0]
        derivative[:, 1] = leftweight * leftjac[:, 0] + (1 - leftweight) * rightjac[:, 0]
        derivative[:, 2] = leftweight * leftjac[:, 1]
        derivative[:, 3] = (1 - leftweight) * rightjac[:, 1]
        derivative[:, 4] = left - right
        if family == 1:
            weight, center, width = values[5:]
            peak, peakjac = gaussian(center, width)
            derivative[:, :5] *= 1 - weight
            derivative[:, 5] = peak - mass
            derivative[:, 6:] = weight * peakjac
            mass = weight * peak + (1 - weight) * mass
        else:
            gapjac = leftweight * leftjac[:, 2] + (1 - leftweight) * rightjac[:, 2]
            derivative[:, 5] = gapjac * gaprange
            derivative[:, 6] = leftweight * leftjac[:, 3] + (1 - leftweight) * rightjac[:, 3]
            if separation < 2.8:
                derivative[:, 0] += gapjac * gapunit * .5
    elif family == 3:
        center, width, skew, shape, notchcenter, notchwidth, depth, shouldercenter, shoulderwidth, weight = values
        background, bgjac = continuum(center, width, skew, shape)
        shoulder, shoulderjac = gaussian(sign * shouldercenter, shoulderwidth)
        shoulderjac[:, 0] *= sign
        delta = OMEGA - notchcenter
        notchprofile = np.exp(-.5 * (delta / notchwidth)**2)
        notch = 1 - depth * notchprofile
        notchjac = np.stack((-depth * notchprofile * delta / notchwidth**2,
                             -depth * notchprofile * delta**2 / notchwidth**3, -notchprofile), axis=1)
        background, bgjac = normalize(background * notch, np.column_stack((bgjac * notch[:, None], background[:, None] * notchjac)))
        shoulder, shoulderjac = normalize(shoulder * notch, np.column_stack((shoulderjac * notch[:, None], shoulder[:, None] * notchjac)))
        mass = (1 - weight) * background + weight * shoulder
        derivative[:, :4] = (1 - weight) * bgjac[:, :4]
        derivative[:, 4:7] = (1 - weight) * bgjac[:, 4:] + weight * shoulderjac[:, 2:]
        derivative[:, 7:9] = weight * shoulderjac[:, :2]
        derivative[:, 9] = shoulder - background
    else:
        center, width, skew, shape, satcenter, satwidth, weight = values
        background, bgjac = continuum(center, width, skew, shape)
        satellite, satjac = gaussian(sign * satcenter, satwidth)
        mass = (1 - weight) * background + weight * satellite
        derivative[:, :4] = (1 - weight) * bgjac
        derivative[:, 4:6] = weight * satjac * np.array([sign, 1])
        derivative[:, 6] = satellite - background
    return mass, derivative * scale

