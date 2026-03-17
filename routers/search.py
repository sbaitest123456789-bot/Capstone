from fastapi import APIRouter, HTTPException
import traceback
from models import SearchQuery
from agents import check_guardrail, mask_pii_with_presidio, run_l1_helpdesk_agent, validate_and_refine_solution

router = APIRouter()

@router.post("/search")
async def search_incidents(request: SearchQuery):
    if check_guardrail(request.query_text):
        raise HTTPException(status_code=400, detail="Blocked: Inappropriate input detected.")
    
    try:
        safe_query = mask_pii_with_presidio(request.query_text)
        agent_result = run_l1_helpdesk_agent(safe_query, request.top_k)
        
        final_suggestion = validate_and_refine_solution(
            safe_query, 
            agent_result.get("raw_context", ""), 
            agent_result["ai_suggestion"]
        )
        
        return {
            "status": "success",
            "original_query": request.query_text,
            "masked_query": safe_query,
            "extracted_filters": agent_result.get("extracted_filters"),
            "ai_suggestion": final_suggestion,
            "reference_documents": agent_result["reference_documents"]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))