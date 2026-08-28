import itertools
import json


BASE = {
    "I": ((1, 0), (0, 1)),
    "raise": ((0, 0), (1, 0)),
    "lower": ((0, 1), (0, 0)),
    "n": ((0, 0), (0, 1)),
    "x": ((0, 1), (1, 0)),
    "y": ((0, 1j), (-1j, 0)),
    "z": ((-1, 0), (0, 1)),
}
Z2_LINK = {
    "I": BASE["I"],
    "x": BASE["z"],
    "z": BASE["x"],
    "y": ((0, -1j), (1j, 0)),
    "raise": ((-0.5, 0.5), (-0.5, 0.5)),
    "lower": ((-0.5, -0.5), (0.5, 0.5)),
}


def sparse(values):
    return tuple((site, int(value)) for site, value in sorted(values.items()) if value)


def local_support(case, channel, anchor):
    length = case["length"]
    touched = {(kind, (anchor + offset) % length)
               for term in channel["terms"] for kind, offset, name in term["ops"]}
    sites = {site for kind, site in touched if kind == "m"}
    for kind, site in touched:
        if kind == "l":
            sites.update((site, (site + 1) % length))
    links = {neighbor for site in sites for neighbor in ((site - 1) % length, site)}
    return sorted(sites), sorted(links), sorted(touched)


def u1_target(links, sites, length):
    if any(value and links.get((site + 1) % length, 0) for site, value in links.items()):
        return None
    return {site: 1 - links[(site - 1) % length] - links[site] for site in sites}


def z2_target(links, sites, length, target):
    return {site: (1 - target[site] * (2 * links[(site - 1) % length] - 1)
                   * (2 * links[site] - 1)) // 2 for site in sites}


def u1_departure(state, sites, length, target):
    sector = {site: (-1) ** site * (state[("m", site)]
              + state[("l", (site - 1) % length)] + state[("l", site)] - 1)
              for site in sites}
    return sparse(sector), sparse(sector)


def z2_departure(state, sites, length, target):
    sector, penalty = {}, {}
    for site in sites:
        charge = state[("m", site)]
        electric = (2 * state[("l", (site - 1) % length)] - 1) * (2 * state[("l", site)] - 1)
        sector[site] = (1 - 2 * charge) * electric - target[site]
        penalty[site] = electric + 2 * target[site] * charge - target[site]
    return sparse(sector), sparse(penalty)


def compile_instance(case, channel, anchor):
    length = case["length"]
    sites, links, touched = local_support(case, channel, anchor)
    keys = sorted([("m", site) for site in sites] + [("l", link) for link in links])
    position = {key: index for index, key in enumerate(keys)}
    terms = []
    for term in channel["terms"]:
        factors = []
        for kind, offset, name in term["ops"]:
            table = Z2_LINK if case["model"] == "z2" and kind == "l" else BASE
            factors.append((position[(kind, (anchor + offset) % length)], table[name]))
        terms.append((complex(*term["amplitude"]), factors))
    transfers = set()
    for bits in itertools.product((0, 1), repeat=len(links)):
        link_state = dict(zip(links, bits))
        if case["model"] == "u1":
            matter = u1_target(link_state, sites, length)
        else:
            matter = z2_target(link_state, sites, length, case["target"])
        if matter is None:
            continue
        state = {("m", site): value for site, value in matter.items()}
        state.update({("l", link): value for link, value in link_state.items()})
        initial = tuple(state[key] for key in keys)
        outputs = {}
        for coefficient, factors in terms:
            branches = [(initial, coefficient)]
            for index, matrix in factors:
                updated = []
                for values, amplitude in branches:
                    for output in (0, 1):
                        element = matrix[output][values[index]]
                        if element:
                            final = values[:index] + (output,) + values[index + 1:]
                            updated.append((final, amplitude * element))
                branches = updated
            for final, amplitude in branches:
                outputs[final] = outputs.get(final, 0) + amplitude
        departure = u1_departure if case["model"] == "u1" else z2_departure
        for final, amplitude in outputs.items():
            if abs(amplitude) > 1e-12:
                sector, penalty = departure(dict(zip(keys, final)), sites, length, case["target"])
                if sector:
                    transfers.add((sector, penalty))
    return transfers


def compile_case(case):
    length = case["length"]
    certificate, cache = [], {}
    for channel in case["channels"]:
        for anchor in channel["anchors"]:
            sites, links, touched = local_support(case, channel, anchor)
            signature = tuple(sorted(((site - anchor) % length, case["target"][site]) for site in sites))
            key = (json.dumps(channel["terms"], sort_keys=True), anchor % 2, signature)
            if key not in cache:
                rows = compile_instance(case, channel, anchor)
                cache[key] = [tuple(tuple(sorted(((site - anchor) % length, value)
                                                 for site, value in vector))
                                    for vector in row) for row in rows]
            rows = {tuple(tuple(sorted(((site + anchor) % length, value)
                                        for site, value in vector))
                          for vector in row) for row in cache[key]}
            certificate.append({"channel": channel["id"], "anchor": anchor,
                                "transfers": [{"sector": list(map(list, sector)),
                                               "penalty": list(map(list, penalty))}
                                              for sector, penalty in sorted(rows)]})
    return certificate


def penalty_rows(certificate):
    rows = set()
    for entry in certificate:
        for transfer in entry["transfers"]:
            vector = tuple(tuple(pair) for pair in transfer["penalty"])
            if vector and vector[0][1] < 0:
                vector = tuple((site, -value) for site, value in vector)
            rows.add(vector)
    return sorted(rows)
