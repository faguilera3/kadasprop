import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.scraper import scrape_infomapa
from app.extractor import extract_data_from_pdf
import os

class AgentState(TypedDict):
    address: str
    pdf_path: Optional[str]
    screenshot_path: Optional[str]
    metadata: Optional[dict]
    extracted_data: Optional[dict]
    error: Optional[str]

async def scrape_node(state: AgentState):
    print(f"Node: Scrape for {state['address']}")
    try:
        output_dir = "data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        result = await scrape_infomapa(state['address'], output_dir)
        return {
            "pdf_path": result["pdf_path"],
            "metadata": result["metadata"],
            "screenshot_path": result.get("screenshot_path")
        }
    except Exception as e:
        return {"error": f"Scraping failed: {str(e)}"}

async def extract_node(state: AgentState):
    print(f"Node: Extract from {state['pdf_path']}")
    
    if state.get("error"):
        return state
        
    try:
        # Pass metadata (specifically Lot number) if available, 
        # though segmentation is handled externally now.
        target_lot = state.get("metadata", {}).get("lote")
        
        data = await extract_data_from_pdf(
            state['pdf_path'], 
            target_lot=target_lot
        )
        return {"extracted_data": data}
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}

# Build Graph
workflow = StateGraph(AgentState)

workflow.add_node("scrape", scrape_node)
workflow.add_node("extract", extract_node)

workflow.set_entry_point("scrape")

workflow.add_edge("scrape", "extract")
workflow.add_edge("extract", END)

app_graph = workflow.compile()
