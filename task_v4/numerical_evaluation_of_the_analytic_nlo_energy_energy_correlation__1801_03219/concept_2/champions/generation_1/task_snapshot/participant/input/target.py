"""Frozen adaptive, embedded Gauss(10)-Kronrod(21) quadrature."""

import heapq
import math

import numpy as np


POSITIVE = np.array([
    .995657163025808080735527280689003,
    .973906528517171720077964012084452,
    .930157491355708226001207180059508,
    .865063366688984510732096688423493,
    .780817726586416897063717578345042,
    .679409568299024406234327365114874,
    .562757134668604683339000099272694,
    .433395394129247190799265943165784,
    .294392862701460198131126603103866,
    .148874338981631210884826001129720,
])
KRONROD_POSITIVE = np.array([
    .011694638867371874278064396062192,
    .032558162307964727478818972459390,
    .054755896574351996031381300244580,
    .075039674810919952767043140916190,
    .093125454583697605535065465083366,
    .109387158802297641899210590325805,
    .123491976262065851077958109831074,
    .134709217311473325928054001771707,
    .142775938577060080797094273138717,
    .147739104901338491374841515972068,
])
GAUSS_POSITIVE = np.array([
    .066671344308688137593568809893332,
    .149451349150580593145776339657697,
    .219086362515982043995534934228163,
    .269266719309996355091226921569469,
    .295524224714752870173892994651338,
])
NODES = np.concatenate((-POSITIVE, [0.0], POSITIVE[::-1]))
KWEIGHTS = np.concatenate((KRONROD_POSITIVE, [.149445554002916905664936468389821], KRONROD_POSITIVE[::-1]))
GWEIGHTS = np.zeros(21)
GWEIGHTS[1:10:2] = GAUSS_POSITIVE
GWEIGHTS[11:21:2] = GAUSS_POSITIVE[::-1]
ATOL = 2e-8
RTOL = 2e-9
MAX_PANELS = 512
PILOT_PANELS = 4


def panel(function, left, right):
    half = (right - left) / 2
    points = (left + right) / 2 + half * NODES
    values = np.asarray(function(points), dtype=np.float64)
    if values.shape != (21,) or not np.isfinite(values).all():
        raise ValueError("integrand must return 21 finite values")
    kronrod = half * math.fsum(KWEIGHTS * values)
    gauss = half * math.fsum(GWEIGHTS * values)
    absolute = half * math.fsum(KWEIGHTS * np.abs(values))
    variation = half * math.fsum(KWEIGHTS * np.abs(values - kronrod / (right - left)))
    embedded = abs(kronrod - gauss)
    error = embedded
    if variation > 0 and embedded > 0:
        error = variation * min(1.0, (200 * embedded / variation) ** 1.5)
    error = max(error, 50 * np.finfo(float).eps * absolute)
    return {"left": left, "right": right, "value": kronrod,
            "error": error, "l1": absolute, "embedded": embedded}


def integrate(function, trace=False):
    """Return a real computed result, conservative local estimates, and status."""
    queue = []
    serial = 0
    evaluations = 0
    pilot = []
    for index in range(PILOT_PANELS):
        pilot.append(panel(function, index / PILOT_PANELS, (index + 1) / PILOT_PANELS))
        evaluations += 21

    def split(parent):
        middle = (parent["left"] + parent["right"]) / 2
        children = [panel(function, parent["left"], middle),
                    panel(function, middle, parent["right"])]
        discrepancy = abs(math.fsum(child["value"] for child in children) - parent["value"])
        for child in children:
            child["error"] = max(child["error"], discrepancy / 2)
        return children

    for parent in pilot:
        for child in split(parent):
            heapq.heappush(queue, (-child["error"], serial, child))
            serial += 1
        evaluations += 42
    while True:
        value = math.fsum(entry[2]["value"] for entry in queue)
        error = math.fsum(entry[2]["error"] for entry in queue)
        absolute = math.fsum(entry[2]["l1"] for entry in queue)
        tolerance = max(ATOL, RTOL * abs(value))
        if error <= tolerance or len(queue) >= MAX_PANELS:
            break
        parent = heapq.heappop(queue)[2]
        for child in split(parent):
            heapq.heappush(queue, (-child["error"], serial, child))
            serial += 1
        evaluations += 42
    result = {"value": value, "estimated_error": error, "tolerance": tolerance,
              "converged": error <= tolerance, "evaluations": evaluations,
              "panels": len(queue), "sampled_l1": absolute}
    if trace:
        result["pilot"] = pilot
        result["leaves"] = sorted((entry[2] for entry in queue), key=lambda leaf: leaf["left"])
    return result
