"""
LangGraph multi-agent flow:

    research -> context -> analyst -> compliance -> decision --(approve)--> publish -----> END
                                                            \\--(review)---> human_review -> END

- research:      calls the MCP TOOL get_stock_price
- context:       reads the two MCP RESOURCES (profile, news)
- analyst:       LLM summarizes price + profile + news
- compliance:     RAG agent — calls the MCP TOOL retrieve_policy_context to
                  pull the most relevant snippets from a local policy
                  knowledge base, then asks the LLM to note any considerations
                  grounded ONLY in that retrieved text
- decision:      LLM classifies approve/review, now informed by the
                  compliance notes — this is the conditional-edge branch point
- publish / human_review: terminal nodes simulating what a real agent fleet
                  would do (e.g. auto-publish a listing vs. pause for a human)
"""

import json
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_anthropic import ChatAnthropic


class AgentState(TypedDict):
    ticker: str
    price_data: dict
    profile: dict
    news: list
    summary: str
    compliance_notes: str
    retrieved_docs: list
    decision: str      # "approve" | "review"
    reason: str
    status: str         # final human-readable outcome


llm = ChatAnthropic(model="claude-sonnet-5")


def _mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient({
        "stock-tools": {
            "command": "python",
            "args": ["mcp_server.py"],
            "transport": "stdio",
        }
    })


async def research_node(state: AgentState) -> AgentState:
    client = _mcp_client()
    tools = await client.get_tools()
    price_tool = next(t for t in tools if t.name == "get_stock_price")
    price = await price_tool.ainvoke({"ticker": state["ticker"]})
    return {**state, "price_data": price}


async def context_node(state: AgentState) -> AgentState:
    client = _mcp_client()
    async with client.session("stock-tools") as session:
        profile = await session.read_resource(f"stock://{state['ticker']}/profile")
        news = await session.read_resource(f"stock://{state['ticker']}/news")
    return {
        **state,
        "profile": profile.contents[0].text,
        "news": news.contents[0].text,
    }


async def analyst_node(state: AgentState) -> AgentState:
    prompt = (
        f"Price data: {state['price_data']}\n"
        f"Company profile: {state['profile']}\n"
        f"Recent news: {state['news']}\n\n"
        "In 2-3 sentences, summarize the current picture for this stock."
    )
    resp = await llm.ainvoke(prompt)
    return {**state, "summary": resp.content}


async def compliance_node(state: AgentState) -> AgentState:
    """
    RAG agent. Retrieves relevant policy snippets from the local knowledge
    base (via the MCP tool retrieve_policy_context), using the analyst's
    summary as the query, then asks the LLM to note considerations grounded
    ONLY in that retrieved text — not general knowledge. This is the
    retrieve-then-generate pattern: the LLM never sees the whole knowledge
    base, only the top-k chunks judged relevant to this specific ticker.
    """
    client = _mcp_client()
    tools = await client.get_tools()
    retrieve_tool = next(t for t in tools if t.name == "retrieve_policy_context")
    retrieved = await retrieve_tool.ainvoke({"query": state["summary"], "top_k": 2})

    # MCP adapter wraps results as list[{"type": "text", "text": "<json_string>", "id": "..."}]
    # Extract and parse the actual content
    parsed_docs = []
    if isinstance(retrieved, list):
        for item in retrieved:
            if isinstance(item, dict) and "text" in item:
                # Parse the JSON string inside the 'text' field
                doc_text = item["text"]
                if isinstance(doc_text, str):
                    try:
                        doc_data = json.loads(doc_text)
                        if isinstance(doc_data, dict):
                            parsed_docs.append(doc_data)
                        elif isinstance(doc_data, list):
                            parsed_docs.extend(doc_data)
                    except json.JSONDecodeError:
                        # Fallback if not JSON
                        parsed_docs.append({"source": "Retrieved", "text": doc_text})
                else:
                    parsed_docs.append(item)

    retrieved = parsed_docs

    if not retrieved:
        return {**state, "compliance_notes": "No relevant policy found.", "retrieved_docs": []}

    # Build context from parsed documents
    context_parts = []
    for doc in retrieved:
        if isinstance(doc, dict):
            source = doc.get("source", "Unknown")
            text = doc.get("text", "")
        else:
            source = "Retrieved"
            text = str(doc)
        context_parts.append(f"[{source}] {text}")

    context_text = "\n\n".join(context_parts)
    prompt = (
        "You are a compliance assistant. Using ONLY the policy excerpts "
        "below — do not use outside knowledge — note any considerations "
        "relevant to this stock summary. If nothing in the excerpts "
        "applies, say so explicitly.\n\n"
        f"Policy excerpts:\n{context_text}\n\n"
        f"Stock summary: {state['summary']}\n\n"
        "Respond in 1-2 sentences."
    )
    resp = await llm.ainvoke(prompt)
    return {**state, "compliance_notes": resp.content, "retrieved_docs": retrieved}


async def decision_node(state: AgentState) -> AgentState:
    """
    The node whose output the conditional edge branches on. In the Amazon-
    Shopify fleet project, this is the same slot the orchestrator fills when
    deciding 'auto-publish the listing' vs 'pause for human approval'.
    """
    prompt = (
        "Based on this summary and the compliance notes, decide whether "
        "it's safe to auto-approve or whether a human should review it "
        "first. Flag for review if there's an error in the underlying "
        "data, if the news sentiment is negative/mixed, or if the "
        "compliance notes raise any concern at all.\n\n"
        f"Summary: {state['summary']}\n"
        f"Raw price data: {state['price_data']}\n"
        f"Compliance notes: {state['compliance_notes']}\n\n"
        'Respond with ONLY this JSON, no other text: '
        '{"decision": "approve" or "review", "reason": "<one short sentence>"}'
    )
    resp = await llm.ainvoke(prompt)
    try:
        parsed = json.loads(resp.content)
    except json.JSONDecodeError:
        parsed = {"decision": "review", "reason": "Could not parse decision output"}
    return {**state, "decision": parsed["decision"], "reason": parsed["reason"]}


def route_decision(state: AgentState) -> Literal["publish", "human_review"]:
    """The routing function LangGraph calls to pick the next edge."""
    return "publish" if state["decision"] == "approve" else "human_review"


async def publish_node(state: AgentState) -> AgentState:
    # Simulates the real "create_shopify_product" / commit action.
    return {**state, "status": f"AUTO-PUBLISHED — {state['reason']}"}


async def human_review_node(state: AgentState) -> AgentState:
    # Simulates pausing the fleet for a human-in-the-loop checkpoint.
    return {**state, "status": f"FLAGGED FOR HUMAN REVIEW — {state['reason']}"}


graph = StateGraph(AgentState)
graph.add_node("research", research_node)
graph.add_node("context", context_node)
graph.add_node("analyst", analyst_node)
graph.add_node("compliance", compliance_node)
graph.add_node("decision", decision_node)
graph.add_node("publish", publish_node)
graph.add_node("human_review", human_review_node)

graph.set_entry_point("research")
graph.add_edge("research", "context")
graph.add_edge("context", "analyst")
graph.add_edge("analyst", "compliance")
graph.add_edge("compliance", "decision")

# --- the conditional edge ---
graph.add_conditional_edges(
    "decision",
    route_decision,
    {"publish": "publish", "human_review": "human_review"},
)

graph.add_edge("publish", END)
graph.add_edge("human_review", END)

app = graph.compile()
