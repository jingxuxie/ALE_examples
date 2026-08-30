import copy


SCORE_DEFINITION = "Minimum ordered high/low Tc ratio over every configured energy family and Matsubara refinement; core_score and worst_family_score intentionally equal score."


def add_reporting_fields(original, resources):
    result = copy.deepcopy(original)
    score = float(result.get("score", 0.))
    result["core_score"] = score
    result["worst_family_score"] = score
    result["score_definition"] = SCORE_DEFINITION
    result["resources"] = resources
    if result.get("valid"):
        reason = "PASS: artifact invariants, target ratio, refinement convergence, and independent audits all passed."
    elif result.get("error"):
        reason = "Evaluation failed: " + str(result["error"])
    elif not result.get("admissible", False):
        reason = "Artifact rejected: matrix invariants or artifact format failed. " + "; ".join(result.get("constraints", {}).get("errors", []))
    elif result.get("physics", {}).get("converged", result.get("converged", True)) is False:
        reason = "Admissible artifact, but Matsubara refinement convergence failed."
    elif result.get("independent", {}).get("passed", result.get("independent_audit_passed", True)) is False:
        reason = "Admissible artifact, but an independent physics audit failed."
    elif score < float(result.get("target_ratio", 1.12)):
        reason = "Admissible artifact, but worst-family/refinement ratio %.12g is below the fixed target %.12g." % (score, float(result.get("target_ratio", 1.12)))
    else:
        reason = "Evaluation incomplete or an additional required validity check failed."
    result["reason"] = reason
    if result.get("score") != original.get("score") or result.get("valid") != original.get("valid"):
        raise AssertionError("reporting must not change numerical scores or verdicts")
    return result
