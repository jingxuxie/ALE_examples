from __future__ import annotations

import hashlib
import json
import math
import random
import os
import stat
from dataclasses import dataclass
from pathlib import Path


FEATURES = {
    "frame_bits", "q_est", "sample_size", "q_se", "latency", "pass_index",
    "first_size", "parity_est", "estimate_ratio", "corrected_fraction",
    "last_corrected_fraction", "last_odd_fraction", "quiet_passes",
    "last_rounds", "last_leak_fraction", "known_per_bit",
}
BASES = {"paper_first", "paper_second", "frame", "first", "estimate", "parity", "remaining"}


def stable_seed(seed: int, label: str) -> int:
    digest = hashlib.sha256(f"cascade-v1:{seed}:{label}".encode()).digest()
    return int.from_bytes(digest[:16], "big")


def reject_duplicates(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"duplicate JSON key: {name}")
        result[name] = value
    return result


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_action(action):
    if not isinstance(action, dict) or not action or set(action) - {"size", "reuse", "batch", "stop"}:
        raise ValueError("invalid action fields")
    if "size" in action:
        size = action["size"]
        if not isinstance(size, dict) or set(size) != {"basis", "scale", "round"}:
            raise ValueError("size requires basis, scale, round")
        if size["basis"] not in BASES or size["round"] not in {"ceil", "nearest", "floor"}:
            raise ValueError("invalid size formula")
        if not finite_number(size["scale"]) or not 0.0625 <= size["scale"] <= 16:
            raise ValueError("scale must be in [1/16,16]")
    if "reuse" in action and action["reuse"] not in {"all", "roots", "recent"}:
        raise ValueError("invalid reuse")
    if "batch" in action and action["batch"] not in {"pass", "smallest"}:
        raise ValueError("invalid batch")
    if "stop" in action and type(action["stop"]) is not bool:
        raise ValueError("stop must be boolean")


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {"version", "max_passes", "schedule", "rules"}:
        raise ValueError("invalid policy fields")
    if type(policy["version"]) is not int or policy["version"] != 1:
        raise ValueError("version must be 1")
    if type(policy["max_passes"]) is not int or not 4 <= policy["max_passes"] <= 20:
        raise ValueError("max_passes must be an integer in [4,20]")
    if not isinstance(policy["schedule"], list) or len(policy["schedule"]) != 4:
        raise ValueError("schedule must contain first, second, third, tail actions")
    for action in policy["schedule"]:
        validate_action(action)
        if set(action) != {"size", "reuse", "batch", "stop"} or action["stop"]:
            raise ValueError("schedule actions must be complete and may not stop")
    if not isinstance(policy["rules"], list) or len(policy["rules"]) > 64:
        raise ValueError("at most 64 rules")
    for rule in policy["rules"]:
        if not isinstance(rule, dict) or set(rule) != {"when", "action"}:
            raise ValueError("rule requires when and action")
        conditions = rule["when"]
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
            raise ValueError("rule requires 1 to 8 conditions")
        for condition in conditions:
            if not isinstance(condition, list) or len(condition) != 3:
                raise ValueError("condition must be [feature, operator, threshold]")
            feature, operator, threshold = condition
            if feature not in FEATURES or operator not in {"lt", "le", "gt", "ge"} or not finite_number(threshold):
                raise ValueError("invalid condition")
        validate_action(rule["action"])
    return policy


def load_policy(path, with_digest=False):
    if not stat.S_ISREG(Path(path).stat().st_mode):
        raise ValueError("policy must be a regular file")
    with Path(path).open("rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("policy must be a regular file")
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError("policy exceeds 64 KiB")
    policy = validate_policy(json.loads(raw, object_pairs_hook=reject_duplicates))
    return (policy, hashlib.sha256(raw).hexdigest()) if with_digest else policy


def choose_action(policy, features):
    action = dict(policy["schedule"][min(features["pass_index"], 3)])
    for rule in policy["rules"]:
        matches = True
        for feature, operator, threshold in rule["when"]:
            value = features[feature]
            matches = matches and {"lt": value < threshold, "le": value <= threshold,
                                   "gt": value > threshold, "ge": value >= threshold}[operator]
        if matches:
            action.update(rule["action"])
            break
    return action


def block_size(size, features):
    frame_bits = features["frame_bits"]
    estimate = max(1 / frame_bits, features["q_est"])
    alpha = math.log2(1 / estimate) - 0.5
    values = {
        "paper_first": 2 ** math.ceil(alpha),
        "paper_second": 2 ** math.ceil((alpha + math.log2(frame_bits / 4)) / 2),
        "frame": frame_bits,
        "first": features["first_size"],
        "estimate": 1 / estimate,
        "parity": 1 / max(1 / frame_bits, features["parity_est"]),
        "remaining": 1 / max(1 / frame_bits, features["parity_est"] - features["corrected_fraction"]),
    }
    exponent = math.log2(max(1, values[size["basis"]] * size["scale"]))
    rounding = {"ceil": math.ceil, "floor": math.floor, "nearest": lambda value: math.floor(value + 0.5)}
    return int(min(frame_bits // 2, max(2, 2 ** rounding[size["round"]](exponent))))


@dataclass
class Node:
    bits: tuple[int, ...]
    mask: int
    pass_index: int
    order: int
    root: bool = False


class Cascade:
    def __init__(self, frame_bits, errors):
        if type(frame_bits) is not int or frame_bits < 4 or frame_bits & (frame_bits - 1):
            raise ValueError("frame_bits must be a power of two >= 4")
        errors = tuple(errors)
        if len(set(errors)) != len(errors) or any(type(bit) is not int or not 0 <= bit < frame_bits for bit in errors):
            raise ValueError("invalid errors")
        self.frame_bits = frame_bits
        self.current = sum(1 << bit for bit in errors)
        self.known = {}
        self.disclosed = 0
        self.rounds = 0
        self.corrected = 0
        self.peak_known = 0

    def odd(self, node):
        return (node.mask & self.current).bit_count() & 1

    def register(self, bits, pass_index, root=False):
        mask = sum(1 << bit for bit in bits)
        if mask not in self.known:
            self.known[mask] = Node(tuple(bits), mask, pass_index, len(self.known), root)
            self.peak_known = max(self.peak_known, len(self.known))
        elif root:
            self.known[mask].root = True
        return self.known[mask]

    def search_batch(self, starts):
        active = list(starts)
        while any(len(node.bits) > 1 for node in active):
            pending = []
            next_active = []
            for node in active:
                while len(node.bits) > 1:
                    midpoint = len(node.bits) // 2
                    left_bits, right_bits = node.bits[:midpoint], node.bits[midpoint:]
                    left_mask = sum(1 << bit for bit in left_bits)
                    right_mask = node.mask ^ left_mask
                    needs_query = left_mask not in self.known and right_mask not in self.known
                    left = self.register(left_bits, node.pass_index)
                    right = self.register(right_bits, node.pass_index)
                    if needs_query:
                        pending.append((left, right))
                        break
                    node = left if self.odd(left) else right
                else:
                    next_active.append(node)
            if pending:
                self.disclosed += len(pending)
                self.rounds += 1
                next_active.extend(left if self.odd(left) else right for left, right in pending)
            active = next_active
        corrected_mask = 0
        for node in active:
            if not self.odd(node) or corrected_mask & node.mask:
                raise RuntimeError("non-disjoint or stale correction")
            corrected_mask |= node.mask
        self.current ^= corrected_mask
        self.corrected += corrected_mask.bit_count()

    def run_pass(self, permutation, size, pass_index, reuse="all", batch="pass"):
        if len(permutation) != self.frame_bits or set(permutation) != set(range(self.frame_bits)):
            raise ValueError("invalid permutation")
        before_disclosed, before_rounds, before_corrected = self.disclosed, self.rounds, self.corrected
        roots = []
        queries = 0
        for offset in range(0, self.frame_bits, size):
            bits = permutation[offset:offset + size]
            mask = sum(1 << bit for bit in bits)
            if mask not in self.known and (pass_index == 0 or offset + size < self.frame_bits):
                queries += 1
            roots.append(self.register(bits, pass_index, True))
        self.disclosed += queries
        self.rounds += int(queries > 0)
        odd_roots = [node for node in roots if self.odd(node)]
        self.search_batch(odd_roots)
        while True:
            candidates = [node for node in self.known.values() if self.odd(node) and
                          (reuse == "all" or node.root or reuse == "recent" and node.pass_index >= pass_index - 1)]
            if not candidates:
                break
            if batch == "pass":
                earliest = min(node.pass_index for node in candidates)
                candidates = [node for node in candidates if node.pass_index == earliest]
            candidates.sort(key=lambda node: (len(node.bits), node.pass_index, node.order))
            occupied = 0
            selected = []
            for node in candidates:
                if not node.mask & occupied:
                    selected.append(node)
                    occupied |= node.mask
            self.search_batch(selected)
        if any(self.odd(node) for node in roots):
            raise RuntimeError("pass did not restore even root parities")
        return {"odd_fraction": len(odd_roots) / len(roots), "odd_roots": len(odd_roots),
                "roots": len(roots), "corrected": self.corrected - before_corrected,
                "disclosed": self.disclosed - before_disclosed, "rounds": self.rounds - before_rounds}


def run_frame(case, frame_seed, policy, errors=None, trace=False):
    frame_bits = case["frame_bits"]
    source = random.Random(stable_seed(frame_seed, "channel"))
    if errors is None:
        errors = [bit for bit in range(frame_bits) if source.random() < case["q_true"]]
    engine = Cascade(frame_bits, errors)
    sample_source = random.Random(stable_seed(frame_seed, "estimate"))
    sample_size = case["sample_size"]
    sample_probability = min(0.15, max(0.0001, case["q_true"] * case["estimate_bias"]))
    sample_errors = sum(sample_source.random() < sample_probability for unused in range(sample_size))
    estimate = min(0.15, max(1 / frame_bits, (sample_errors + 0.5) / (sample_size + 1)))
    features = dict.fromkeys(FEATURES, 0.0)
    features.update(frame_bits=frame_bits, q_est=estimate, sample_size=sample_size,
                    q_se=math.sqrt(estimate * (1 - estimate) / (sample_size + 1)),
                    latency=case["latency"], parity_est=estimate, estimate_ratio=1.0,
                    first_size=block_size({"basis": "paper_first", "scale": 1, "round": "nearest"},
                                          {"frame_bits": frame_bits, "q_est": estimate,
                                           "first_size": 2, "parity_est": estimate, "corrected_fraction": 0}))
    history = []
    for pass_index in range(policy["max_passes"]):
        features["pass_index"] = pass_index
        action = choose_action(policy, features)
        if pass_index >= 3 and action["stop"]:
            break
        size = block_size(action["size"], features)
        permutation = list(range(frame_bits))
        random.Random(stable_seed(frame_seed, f"permutation:{pass_index}")).shuffle(permutation)
        stats = engine.run_pass(permutation, size, pass_index, action["reuse"], action["batch"])
        if trace:
            history.append({"features": dict(features), "action": action, "size": size, **stats})
        if pass_index == 0:
            features["first_size"] = size
            odd_probability = min(0.499, (stats["odd_roots"] + 0.5) / (stats["roots"] + 1))
            features["parity_est"] = min(0.15, max(1 / frame_bits, (1 - (1 - 2 * odd_probability) ** (1 / size)) / 2))
            features["estimate_ratio"] = features["parity_est"] / estimate
        features.update(corrected_fraction=engine.corrected / frame_bits,
                        last_corrected_fraction=stats["corrected"] / frame_bits,
                        last_odd_fraction=stats["odd_fraction"], last_rounds=stats["rounds"],
                        last_leak_fraction=stats["disclosed"] / frame_bits,
                        known_per_bit=len(engine.known) / frame_bits,
                        quiet_passes=features["quiet_passes"] + 1 if stats["corrected"] == 0 else 0)
    failure = bool(engine.current)
    disclosed = engine.disclosed + 32
    rounds = engine.rounds + 1
    entropy = -case["q_true"] * math.log2(case["q_true"]) - (1 - case["q_true"]) * math.log2(1 - case["q_true"])
    leakage = 1.0 if failure else min(1.0, disclosed / frame_bits)
    result = {"failure": int(failure), "residual_bits": engine.current.bit_count(),
              "disclosed": disclosed, "rounds": rounds, "passes": pass_index if action["stop"] and pass_index >= 3 else pass_index + 1,
              "peak_known": engine.peak_known, "effective_leakage": leakage,
              "cost": leakage / entropy + case["latency"] * rounds}
    if trace:
        result["trace"] = history
    return result
