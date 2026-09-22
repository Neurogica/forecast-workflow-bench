"""Complete-cohort aggregation for the versioned multi-domain LM track."""

from collections import Counter
from math import fsum, isclose, isfinite


def case_weights(cases, cohort_weights):
    """Equal series/lead groups within cohorts, with explicit cohort weights.

    Target dates are averaged inside a series/lead group. Missing cases must not
    cause a surviving group to gain weight, so callers supply the frozen index.
    """
    cases = list(cases)
    ids = [c["case_id"] for c in cases]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("A nonempty unique case index is required")
    if set(c["cohort"] for c in cases) != set(cohort_weights):
        raise ValueError("Cohort weights must cover exactly the frozen cohorts")
    if any(not isfinite(w) or w <= 0 for w in cohort_weights.values()):
        raise ValueError("Cohort weights must be finite and positive")
    if not isclose(fsum(cohort_weights.values()), 1.0, abs_tol=1e-12):
        raise ValueError("Cohort weights must sum to one")
    groups = Counter((c["cohort"], c["authority"], c["family"]) for c in cases)
    counts = Counter(k[0] for k in groups)
    return {
        c["case_id"]: cohort_weights[c["cohort"]]
        / counts[c["cohort"]]
        / groups[c["cohort"], c["authority"], c["family"]]
        for c in cases
    }


def complete_weighted_mean(values, weights):
    """Reject partial rankings, unexpected cases and nonfinite scores."""
    if set(values) != set(weights):
        raise ValueError("Ranked results must cover exactly the complete frozen case set")
    if not values or any(not isfinite(v) for v in values.values()):
        raise ValueError("Scores must be finite")
    if any(not isfinite(w) or w <= 0 for w in weights.values()):
        raise ValueError("Weights must be finite and positive")
    if not isclose(fsum(weights.values()), 1.0, abs_tol=1e-12):
        raise ValueError("Weights must sum to one")
    return fsum(values[cid] * weights[cid] for cid in sorted(weights))
