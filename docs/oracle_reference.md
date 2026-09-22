# Oracle diagnostics and forecast costs

The published Language Model track ranks all models on the same case set and
forecast budget. Loss, completion and forecast credits remain separate outputs.
The utilities below support offline analysis; they do not change the published
ranking or expose target observations through agent tools.

## Two distinct references

A **perfect-demand optimum** minimizes realized decision loss with exact target
observations while retaining the action grid, commitment duration and ramp limits.
Its loss can be nonzero even with perfect forecasts.

A **finite-menu oracle** chooses among a fixed set of forecast-derived plans.
Generate these plans without target access, record the tariff for each execution,
and then use targets offline to score and select candidates. Within a budget,
select the lowest-loss candidate, resolving exact ties by lower credits and name.
This oracle pays only for the chosen execution, not for searching the entire menu.
It is a hindsight diagnostic, not a deployable agent or a lower bound on every
plan an agent could construct.

```python
from forecast_workflow.evaluation.oracle import Candidate, frontier, matched_gap, select

# Illustrative values, not benchmark results.
menu = [
    Candidate("classical", loss=0.10, credits=0),
    Candidate("forecast_a", loss=0.05, credits=10),
    Candidate("forecast_b", loss=0.06, credits=20),
]
best_affordable = select(menu, budget=10)
nondominated_plans = frontier(menu)
gap = matched_gap(loss=0.08, spent=10, candidates=menu)
```

The catalog gap is the agent's realized loss minus the oracle loss affordable at
its actual expenditure. Aggregate per-case gaps with the same authority-lead
weights used for primary loss. Do not apply an average credit allowance to every
case, and do not clip negative gaps: an agent may outperform this finite menu.
For the same case, lowering loss or expenditure cannot worsen the gap.

## Legacy diagnostic: not a cost-inclusive score

Both a perfect free-menu selector and a perfect paid-menu selector have zero gap,
even when the paid selector produces lower decision loss. Minimizing gap and then
credits would therefore discourage further improvements beyond the free menu.
The metric also depends on the candidate menu and does not guarantee preservation
of aggregate-average dominance when models allocate credits differently.

Use the gap as a diagnostic alongside raw loss and credits. A future aggregate
budget track should predeclare common budgets and aggregation weights, execute
all models at every budget, and report the individual conditions as well as their
aggregate. A single monetary score instead needs an externally justified exchange
rate between forecast costs and operational loss. Do not tune that rate to select
a preferred winner.

Record the candidate menu, model revisions, context/horizon settings, input hashes,
scoring version, budget and selection rule. Keep all oracle targets and selection
outputs outside evaluated agent access. Forecast-service credits are not total
LLM deployment costs; report API and hardware measurements separately when used.


## Cost-aware gap v2

The paper now reports an explicit cost-aware objective on the common case budget:

`J_lambda = loss + lambda * spent / B`

`G_lambda = macro(J_agent - min_affordable_menu J_plan)`

Every candidate uses the same budget `B`, rather than a budget equal to the
agent's realized spending. The oracle minimizes the **same** objective as the
agent. It may therefore prefer a cheaper, slightly less accurate plan. At any
positive lambda, extra spending strictly worsens the score at fixed loss, even
when the menu's best affordable forecast does not change. Oracle subtraction is
constant across models on a common cohort, so ranking equals penalized loss and
preserves aggregate loss/credit dominance under the same averaging weights.
Negative gaps remain valid for agents that beat the finite menu.

```python
from forecast_workflow.evaluation.oracle import cost_aware_gap, select_cost_aware

reference = select_cost_aware(menu, budget=100, cost_weight=0.01)
score = cost_aware_gap(loss=0.08, spent=10, candidates=menu,
                       budget=100, cost_weight=0.01)
```

`configs/cost-aware-v2.json` records the positive common budget, weight and sweep.
The paper uses lambda=0.01 as an **illustrative post-hoc convention**: full-budget
use costs 0.01 normalized loss. This choice was made after the primary results
were available; it is neither an externally calibrated business price nor a
preregistered metric. There is no universally preferred coefficient. The complete
sensitivity sweep is published, not only the setting favorable to a particular
policy. Values at different lambda settings are different objectives and should
not be compared as if an agent's performance changed.

| Lambda | Empirical G | Router G | Astra G | Best of all measured agents/policies |
|---:|---:|---:|---:|---|
| 0 | 0.020649 | 0.018253 | 0.016716 | gpt-6-astra |
| 0.001 | 0.020473 | 0.018519 | 0.017528 | gpt-6-astra |
| 0.003 | 0.020180 | 0.019111 | 0.019214 | fixed_dev_route |
| 0.01 | 0.019568 | 0.021594 | 0.025527 | fixed_hour_of_day_empirical |
| 0.03 | 0.018802 | 0.029674 | 0.044546 | fixed_hour_of_day_empirical |
| 0.1 | 0.017992 | 0.059823 | 0.112985 | fixed_hour_of_day_empirical |

At lambda=0.01, the cost-aware oracle has loss 0.032540 and 6,839 mean credits;
G is zero for that reference. A free-menu oracle and a loss-only menu oracle need
not have zero G under the cost-aware objective. Both remain hindsight diagnostics,
not agents. The original `matched_gap` function remains available only to reproduce
historical analyses; it is no longer the paper's G column.

[Full aggregate results](../results/cost-aware-v2.json) preserve the sweep. These
are local revised analyses; the published primary-377 loss leaderboard has not
been overwritten or silently reranked. Credits still exclude LLM inference cost.
