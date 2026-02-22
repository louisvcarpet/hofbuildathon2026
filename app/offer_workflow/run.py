# app/offer_workflow/run.py

from langgraph.graph import StateGraph, START, END
from app.offer_workflow.state import OfferWorkflowState
from app.node1_extract.databricks_node import DatabricksNode
from app.node2_reason.nemotron_node import NemotronNode
from app.node3_verify.output_checker import OutputChecker
import asyncio


def router(state: OfferWorkflowState):

    if state.tryout > state.maxtry:
        state.output_checker = "yes"
        state.result = {"error": "Max retries exceeded."}
        return END

    elif state.output_checker == "yes":
        return END

    elif state.output_checker == "no":
        return "reason"


async def run_offer_workflow(input_payload: dict):

    extractNode = DatabricksNode()
    reasonNode = NemotronNode()
    verifyNode = OutputChecker()

    workflow = StateGraph(OfferWorkflowState)

    workflow.add_node("extract", extractNode)
    workflow.add_node("reason", reasonNode)
    workflow.add_node("verify", verifyNode)

    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "reason")
    workflow.add_edge("reason", "verify")

    workflow.add_conditional_edges(
        "verify",
        router,
        {
            END: END,
            "reason": "reason",
        }
    )

    graph = workflow.compile()

    return await graph.ainvoke(
        OfferWorkflowState(**input_payload)
    )


if __name__ == "__main__":

    sample_input = {
        "job_title": "Senior Software Engineer",
        "industry": "FinTech",
        "company_tier": "Tier1",
        "location": "NYC",
        "base_salary": 155000,
        "bonus_pct": 15,
        "equity_val": 90000,
        "signing_bonus": 20000,
        "years_exp": 6,
        "remote_status": "Hybrid"
    }

    result = asyncio.run(run_offer_workflow(sample_input))
    print(result)