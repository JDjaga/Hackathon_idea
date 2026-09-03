"""
HomeMind — "Ask My House" RAG API Route
Provides natural language household query endpoint with grounded evidence.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.passport_store import get_passport_store
from app.core.household_rag import answer_household_query

router = APIRouter(prefix="/api/ask", tags=["Ask My House RAG"])
store = get_passport_store()


class AskQueryRequest(BaseModel):
    query: str = Field(..., example="When does my washing machine warranty expire?")
    passport_id: Optional[str] = Field(None, description="Optional Point-and-Ask product scope")


@router.post("")
async def ask_household(req: AskQueryRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    products = store.get_all()
    result = answer_household_query(req.query, products, scoped_passport_id=req.passport_id)
    result["query"] = req.query
    result["scoped_passport_id"] = req.passport_id
    return result
