# app/offer_workflow/node1_extract/databricks_node.py

class DatabricksNode:

    async def __call__(self, state):

        # Pure extraction from state (no logic)
        state.market_data = {
            "job_title": state.job_title,
            "industry": state.industry,
            "company_tier": state.company_tier,
            "location": state.location,
            "base_salary": state.base_salary,
            "bonus_pct": state.bonus_pct,
            "equity_val": state.equity_val,
            "signing_bonus": state.signing_bonus,
            "years_exp": state.years_exp,
            "remote_status": state.remote_status,
        }

        return state