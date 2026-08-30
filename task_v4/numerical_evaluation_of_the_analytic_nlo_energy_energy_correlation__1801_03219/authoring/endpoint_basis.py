import mpmath as mp


def leading_terms():
    zeta2, zeta3 = mp.zeta(2), mp.zeta(3)
    subleading_left = [-25*zeta2/12+zeta3/2+mp.mpf(17683)/2700, -mp.mpf(107)/120]
    leading_left = [43*zeta2/12-zeta3-mp.mpf(8263)/1728+2*subleading_left[0],
                    mp.mpf(25)/32+2*subleading_left[1]]
    flavor_left = [-mp.mpf(4913)/3600, mp.mpf(53)/240]
    subleading_right = [11*zeta2/4+3*zeta3/2-mp.mpf(35)/16,
                        zeta2/2-mp.mpf(35)/72, mp.mpf(11)/12, mp.mpf(0)]
    leading_right = [3*zeta2-zeta3+mp.mpf(45)/16+2*subleading_right[0],
                     zeta2+mp.mpf(17)/4+2*subleading_right[1],
                     mp.mpf(9)/4+2*subleading_right[2], mp.mpf(1)/2]
    flavor_right = [mp.mpf(3)/4-zeta2, mp.mpf(1)/18, -mp.mpf(1)/3, mp.mpf(0)]
    return {"collinear": [leading_left,subleading_left,flavor_left],
            "backward": [leading_right,subleading_right,flavor_right]}


def native_chart(coordinate, chart, native):
    angular = 1/(1+mp.exp(-coordinate))
    complement = 1/(1+mp.exp(coordinate))
    channels = native._components(angular)
    if chart == "density":
        return [angular*complement*value for value in channels]
    logarithm = mp.log(angular if chart == "collinear" else complement)
    denominator = angular if chart == "collinear" else complement
    parameters = leading_terms()[chart]
    leading = [mp.polyval(list(reversed(values)), logarithm)/denominator for values in parameters]
    return [value-base for value,base in zip(channels,leading)]
