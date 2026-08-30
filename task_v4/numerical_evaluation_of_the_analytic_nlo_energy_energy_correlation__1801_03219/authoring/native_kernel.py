"""High-precision reference implementation for the NLO angular coefficient."""

import mpmath as mp


def _p(z, c):
    out = mp.mpf("0")
    for a in reversed(c):
        out = out * z + a
    return out


def _basis(z):
    lz = mp.log(z)
    l1 = mp.log1p(-z)
    r = mp.sqrt(z)
    z2 = mp.zeta(2)
    z3 = mp.zeta(3)
    li2z = mp.polylog(2, z)
    lm = mp.polylog(3, -z / (1-z))
    g11 = l1
    g12 = lz
    g21 = l1*l1 + 2*(li2z + z2)
    g22 = mp.polylog(2, 1-z) - li2z
    g23 = lz*mp.log((1-r)/(1+r)) - 2*mp.polylog(2, -r) + 2*mp.polylog(2, r)
    g24 = z2
    g31 = -(-l1+lz)*g21 - 6*(lm-z3)
    g32 = l1**3 + 6*l1*li2z - 12*(mp.polylog(3, z)+lm)
    g33 = l1**3 - 12*mp.polylog(3, z) + 6*l1*(li2z-z2)
    g34 = lm - 3*lz*z2 + 8*z3
    g35 = (mp.log((1+r)/(1-r))**2 * mp.log((1-z)/z)
           - 8*(mp.polylog(3, -r/(1-r)) + mp.polylog(3, r/(1+r)))
           + 2*lm + 4*l1*z2)
    return g11,g12,g21,g22,g23,g24,g31,g32,g33,g34,g35


def _components(z):
    g11,g12,g21,g22,g23,g24,g31,g32,g33,g34,g35 = _basis(z)
    om = 1-z

    blc = _p(z,[63298,-143577,72305,2064,-31000,157060,-244800,122400])/(1440*om*z**4)
    blc -= _p(z,[3007,-9329,11309,-6201,2716,-48122,283140,-667280,673200,-244800])*g11/(720*om*z**5)
    blc -= _p(z,[19938,-38295,17261,-336,13052,-126900,422480,-550800,244800])*g12/(720*om*z**4)
    blc += _p(z,[87,-211,296,-96,25,-17,10,4])*g21/(24*om*z**5)
    blc += _p(z,[3323,-4726,1126,-160,-320,4040,-28480,61200,-40800])*g22/(120*z**5)
    blc -= (1-11*z)*g23/(48*z**mp.mpf("3.5"))
    blc -= _p(z,[4193,-10159,8812,-2246,160,60,120])*g24/(120*om*z**5)
    blc -= 2*_p(z,[3,-31,116,-170,85])*g31
    blc += _p(z,[5,-21,18,-4])*g32/(6*om*z**5)
    blc += (1+z*z)*g33/(12*om)

    bnlc = _p(z,[9320,-27552,14966,902,-17359,75748,-115200,57600])/(720*om*z**4)
    bnlc -= _p(z,[4880,-12412,11322,-3571,3225,-31035,147846,-321680,316800,-115200])*g11/(360*om*z**5)
    bnlc -= _p(z,[11424,-25029,10971,-742,18696,-138600,412960,-518400,230400])*g12/(720*om*z**4)
    bnlc += _p(z,[314,-760,721,-140,15,-184,235,-91])*g21/(120*om*z**5)
    bnlc += _p(z,[952,-1431,315,-40,-340,2660,-14680,28800,-19200])*g22/(60*z**5)
    bnlc += _p(z,[1435,547,992,-160,960])*g23/(480*z**mp.mpf("3.5"))
    bnlc -= _p(z,[1266,-3143,2647,-585,-130,120,-120])*g24/(60*om*z**5)
    bnlc += _p(z,[3,-42,318,-1196,2196,-1920,640])*g31/(4*om*z)
    bnlc += _p(z,[1,-9,9,-1,-1,3,-3,2])*g32/(12*om*z**5)
    bnlc -= (1-2*z)*(1-z+z*z)*g34/(2*om*z)
    bnlc -= _p(z,[3,0,1,2,-1,2])*g35/(4*z**4)

    bnf = -_p(z,[2050,-4115,1825,48,-1568,8852,-14400,7200])/(144*om*z**4)
    bnf -= _p(z,[1801,-4801,3269,-489,-100,10960,-77700,193040,-198000,72000])*g11/(360*om*z**5)
    bnf += _p(z,[561,-939,428,10,1190,-16650,60520,-81000,36000])*g12/(180*om*z**4)
    bnf += _p(z,[9,-24,18,-4,0,0,0,-1])*g21/(6*om*z**5)
    bnf -= _p(z,[187,-222,72,0,0,920,-7840,18000,-12000])*g22/(60*z**5)
    bnf += (1-3*z)*g23/(48*z**mp.mpf("3.5"))
    bnf += _p(z,[7,71,-66,8])*g24/(60*om*z**5)
    bnf += 2*_p(z,[1,-16,66,-100,50])*g31
    return blc, bnlc, bnf


def nlo_coefficient(z, ca, cf, tf, nf):
    """Return B(z) for 0 < z < 1 and real color parameters."""
    with mp.workdps(70):
        z,ca,cf,tf,nf = map(mp.mpf, (z,ca,cf,tf,nf))
        if not 0 < z < 1:
            raise ValueError("z must be in (0,1)")
        blc,bnlc,bnf = _components(z)
        ans = cf*cf*blc + cf*(ca-2*cf)*bnlc + cf*nf*tf*bnf
        return float(mp.re(ans))


if __name__ == "__main__":
    print(nlo_coefficient(0.5, 3, 4/3, 0.5, 5))
