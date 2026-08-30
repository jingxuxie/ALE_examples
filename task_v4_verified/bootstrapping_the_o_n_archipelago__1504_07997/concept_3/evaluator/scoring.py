import numpy as np

from model import FAMILIES, SCALES, TARGETS, canonical_angle


def score_case(instance, estimate, radii):
    error = np.asarray(estimate) - instance.target()
    error[-1] = canonical_angle(error[-1])
    error = np.abs(error)
    radii = np.asarray(radii)
    point = error / SCALES
    interval = (2 * radii + 20 * np.maximum(error - radii, 0)) / (4 * SCALES)
    combined = 0.7 * point + 0.3 * interval
    return {
        "point_loss": float(point.mean()), "interval_loss": float(interval.mean()),
        "loss": float(combined.mean()), "coverage90": float(np.mean(error <= radii)),
        "target_point_losses": dict(zip(TARGETS, point.tolist())),
        "target_covered": dict(zip(TARGETS, (error <= radii).tolist())),
    }


def aggregate(cases, target, official):
    groups = {}
    for family in FAMILIES:
        selected = [case for case in cases if case["family"] == family]
        valid = [case for case in selected if case["status"] == "ok"]
        group = {"count": len(selected), "valid": len(valid)}
        for key in ("loss", "point_loss", "interval_loss", "coverage90"):
            group[key] = float(np.mean([case[key] for case in valid])) if valid else None
        groups[family] = group
    all_valid = bool(cases) and all(case["status"] == "ok" for case in cases)
    complete = all(group["count"] for group in groups.values())
    runtime_seconds = float(sum(case.get("runtime_seconds", case.get("elapsed_seconds", 0.0)) for case in cases))
    runtime_score = 100 * max(0.0, 1 - runtime_seconds / (45 * len(cases))) if cases else 0.0
    result = {
        "families": groups, "valid": all_valid, "official": official, "passed": False,
        "runtime_seconds": runtime_seconds,
        "runtime_score": runtime_score if all_valid and complete else 0.0,
    }
    if not all_valid or not complete:
        invalid_count = sum(case["status"] != "ok" for case in cases)
        reasons = []
        if invalid_count:
            reasons.append(f"{invalid_count} invalid case(s); see per-case reasons")
        if not complete:
            reasons.append("incomplete public-family coverage")
        result.update({
            "robust_loss": None, "core_score": 0.0,
            "worst_family_loss": None, "worst_family_score": 0.0,
            "reason": "; ".join(reasons) or "empty evaluation",
        })
        return result
    mean_loss = float(np.mean([group["loss"] for group in groups.values()]))
    worst_loss = max(group["loss"] for group in groups.values())
    robust_loss = 0.35 * mean_loss + 0.65 * worst_loss
    worst_point = max(group["point_loss"] for group in groups.values())
    coverage = float(np.mean([group["coverage90"] for group in groups.values()]))
    worst_coverage = min(group["coverage90"] for group in groups.values())
    checks = {
        "robust_loss": robust_loss <= target["max_robust_loss"],
        "worst_family_point_loss": worst_point <= target["max_worst_family_point_loss"],
        "coverage90": coverage >= target["min_coverage90"],
        "worst_family_coverage90": worst_coverage >= target["min_worst_family_coverage90"],
        "official_suite": official,
    }
    result.update({
        "mean_loss": mean_loss, "worst_family_loss": worst_loss,
        "robust_loss": robust_loss, "core_score": 100 / (1 + robust_loss),
        "worst_family_score": 100 / (1 + worst_loss),
        "worst_family_point_loss": worst_point, "coverage90": coverage,
        "worst_family_coverage90": worst_coverage,
        "target_checks": checks, "passed": all(checks.values()),
        "reason": "All frozen target checks passed." if all(checks.values()) else (
            "Failed checks: " + ", ".join(key for key, passed in checks.items() if not passed) + "."
        ),
    })
    return result
