"""Finite-menu hindsight references, never exposed to an evaluated agent.

These references are optimal only among supplied plans. They are not lower
bounds on an agent that may construct other plans or use different histories.
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Candidate:
    name: str
    loss: float
    credits: int

    def __post_init__(self):
        if not isfinite(self.loss) or self.loss < 0:
            raise ValueError("Loss must be finite and nonnegative")
        if isinstance(self.credits, bool) or not isinstance(self.credits, int) or self.credits < 0:
            raise ValueError("Credits must be a nonnegative integer")


def select(candidates: list[Candidate], budget: int) -> Candidate:
    """Minimize realized loss, then credits, then name within a case budget."""
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("Budget must be a nonnegative integer")
    feasible = [c for c in candidates if c.credits <= budget]
    if not feasible:
        raise ValueError("No affordable reference plan")
    return min(feasible, key=lambda c: (c.loss, c.credits, c.name))


def frontier(candidates: list[Candidate]) -> list[Candidate]:
    """Return nondominated plans in increasing credit order; resolve duplicates."""
    result = []
    for candidate in sorted(candidates, key=lambda c: (c.credits, c.loss, c.name)):
        if not result or candidate.loss < result[-1].loss:
            result.append(candidate)
    return result


def matched_gap(loss: float, spent: int, candidates: list[Candidate]) -> float:
    """Signed loss gap at the agent's actual expenditure, without tuned weights.

    Negative gaps are retained: the finite menu need not contain an agent's plan.
    For the same case, lowering loss or credits cannot worsen this metric.
    Legacy diagnostic only: spending on an oracle plateau is unpenalized.
    Do not use this as a cost-inclusive ranking score.
    """
    if not isfinite(loss):
        raise ValueError("Loss must be finite")
    return loss - select(candidates, spent).loss


def penalized_loss(loss: float, spent: int, budget: int, cost_weight: float) -> float:
    """Loss plus an explicit full-budget cost, using a common positive budget."""
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("A positive integer common budget is required")
    if isinstance(spent, bool) or not isinstance(spent, int) or not 0 <= spent <= budget:
        raise ValueError("Expenditure must be an integer within the common budget")
    if not isfinite(loss) or loss < 0:
        raise ValueError("Loss must be finite and nonnegative")
    if isinstance(cost_weight, bool) or not isfinite(cost_weight) or cost_weight < 0:
        raise ValueError("Cost weight must be finite and nonnegative")
    return loss + cost_weight * spent / budget


def select_cost_aware(candidates: list[Candidate], budget: int, cost_weight: float) -> Candidate:
    """Hindsight minimizer of the same loss-cost objective used for agents."""
    penalized_loss(0, 0, budget, cost_weight)
    feasible = [c for c in candidates if c.credits <= budget]
    if not feasible:
        raise ValueError("No affordable reference plan")
    return min(
        feasible,
        key=lambda c: (penalized_loss(c.loss, c.credits, budget, cost_weight), c.credits, c.name),
    )


def cost_aware_gap(
    loss: float, spent: int, candidates: list[Candidate], budget: int, cost_weight: float
) -> float:
    """Signed penalized-loss regret to a common-budget finite-menu oracle.

    The reference does not depend on the agent's expenditure. At positive weight,
    increasing spend strictly worsens the score at fixed loss, even on menu plateaus.
    Negative values are valid when an agent beats the finite menu. Across a common
    cohort, ranking is identical to penalized loss because the subtracted oracle
    and macro weights are shared. This does not remove the need to justify weight.
    """
    objective = penalized_loss(loss, spent, budget, cost_weight)
    oracle = select_cost_aware(candidates, budget, cost_weight)
    return objective - penalized_loss(oracle.loss, oracle.credits, budget, cost_weight)
