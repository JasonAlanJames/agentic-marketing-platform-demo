import json
import os
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()


class MarketingEmail(BaseModel):
    subject: str
    preview: str
    body: str
    cta: str


class ComplianceReview(BaseModel):
    approved: bool
    score: int = Field(ge=0, le=10)
    issues: list[str]
    revision_instructions: str


class MarketingState(TypedDict, total=False):
    source_document: str
    audience: str
    draft: dict
    review: dict
    revision_count: int
    final_output: dict


model = ChatBedrockConverse(
    model_id="amazon.nova-lite-v1:0",
    region_name=os.getenv("AWS_REGION", "us-west-2"),
    temperature=0.1,
    max_tokens=1500,
)

writer_model = model.with_structured_output(MarketingEmail)
reviewer_model = model.with_structured_output(ComplianceReview)

langfuse_handler = CallbackHandler()


def writer_node(state: MarketingState) -> MarketingState:
    prior_review = state.get("review", {})
    revision_guidance = prior_review.get("revision_instructions", "")

    prompt = f"""
You are a financial-services marketing writer.

Audience:
{state["audience"]}

SOURCE DOCUMENT:
{state["source_document"]}

Rules:
1. Use only facts explicitly contained in the source document.
2. Do not invent products, statistics, guarantees, fees, disclosures,
   performance claims, investor benefits, or suitability claims.
3. Do not claim that the strategy will maximize savings, increase returns,
   reduce risk, or benefit a portfolio unless the source explicitly says so.
4. If information is absent, omit it.
5. Maintain a professional, educational tone.
6. Return the required structured output.

REVIEWER REVISION GUIDANCE:
{revision_guidance or "No prior review. Create the initial draft."}
"""

    result = writer_model.invoke(prompt)

    return {
        "draft": result.model_dump(),
        "revision_count": state.get("revision_count", 0),
    }


def reviewer_node(state: MarketingState) -> MarketingState:
    prompt = f"""
You are a strict financial-marketing compliance reviewer.

Compare the generated email with the source document.

SOURCE DOCUMENT:
{state["source_document"]}

GENERATED EMAIL:
{json.dumps(state["draft"], indent=2)}

Fail the email if it includes:
- Facts not supported by the source
- Invented products or strategies
- Unsupported benefit or performance claims
- Suitability recommendations
- Guarantees or promises
- Claims about reducing risk or maximizing savings
- Any contradiction of the source

Set approved=true only if the email is fully grounded and compliant.

Return:
- approved
- score from 0 to 10
- issues
- exact revision instructions
"""

    result = reviewer_model.invoke(prompt)

    return {
        "review": result.model_dump(),
    }


def increment_revision_node(state: MarketingState) -> MarketingState:
    return {
        "revision_count": state.get("revision_count", 0) + 1,
    }


def finalize_node(state: MarketingState) -> MarketingState:
    return {
        "final_output": state["draft"],
    }


def route_after_review(
    state: MarketingState,
) -> Literal["finalize", "revise"]:
    if state["review"]["approved"]:
        return "finalize"

    if state.get("revision_count", 0) >= 2:
        return "finalize"

    return "revise"


builder = StateGraph(MarketingState)

builder.add_node("writer", writer_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("revise", increment_revision_node)
builder.add_node("finalize", finalize_node)

builder.add_edge(START, "writer")
builder.add_edge("writer", "reviewer")

builder.add_conditional_edges(
    "reviewer",
    route_after_review,
    {
        "finalize": "finalize",
        "revise": "revise",
    },
)

builder.add_edge("revise", "writer")
builder.add_edge("finalize", END)

graph = builder.compile()


def main() -> None:
    initial_state: MarketingState = {
        "source_document": (
            "Capital Group is introducing a new retirement planning strategy "
            "designed for long-term investors seeking stability during market "
            "volatility. The strategy emphasizes diversification, disciplined "
            "investing, and tax-efficient retirement income planning."
        ),
        "audience": "Financial advisors",
        "revision_count": 0,
    }

    result = graph.invoke(
        initial_state,
        config={
            "callbacks": [langfuse_handler],
            "metadata": {
                "project": "capital-group-agentic-marketing-demo",
                "environment": "development",
            },
            "tags": [
                "langgraph",
                "bedrock",
                "marketing",
                "compliance",
            ],
        },
    )

    print("\n=== FINAL EMAIL ===")
    print(json.dumps(result["final_output"], indent=2))

    print("\n=== COMPLIANCE REVIEW ===")
    print(json.dumps(result["review"], indent=2))

    print("\n=== REVISION COUNT ===")
    print(result["revision_count"])


if __name__ == "__main__":
    main()