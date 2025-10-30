# file: graph_flow.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from tools import check_kenteken, rdw_lookup, bing_image_search


# --- Define our state ---
class CarState(TypedDict):
    kenteken: str
    merk_type: str
    valid: bool | None
    rdw_info: dict | None
    search_query: str | None
    images: list | None


# --- Define the nodes (functions) ---
async def check_kenteken_node(state: CarState) -> CarState:
    valid = await check_kenteken(state["kenteken"])
    return {**state, "valid": valid}


async def rdw_lookup_node(state: CarState) -> CarState:
    if not state["valid"]:
        return {**state, "rdw_info": {"found": False, "error": "Ongeldig kenteken"}}
    rdw_info = await rdw_lookup(state["kenteken"])
    return {**state, "rdw_info": rdw_info}


async def bing_search_node(state: CarState) -> CarState:
    info = state["rdw_info"]
    merk_type = state["merk_type"]
    kenteken = state["kenteken"]

    # Bouw query
    if info.get("found"):
        query = f"{info['merk']} {info['handelsbenaming']} {kenteken}"
    else:
        query = f"{merk_type} {kenteken}"

    images = await bing_image_search(query)
    return {**state, "search_query": query, "images": images}


# --- Graph constructie ---
def build_graph():
    graph = StateGraph(CarState)

    graph.add_node("check_kenteken", check_kenteken_node)
    graph.add_node("rdw_lookup", rdw_lookup_node)
    graph.add_node("bing_search", bing_search_node)

    # edges (data flow)
    graph.add_edge("check_kenteken", "rdw_lookup")
    graph.add_edge("rdw_lookup", "bing_search")
    graph.add_edge("bing_search", END)

    graph.set_entry_point("check_kenteken")
    return graph.compile()
