"""
HomeMind — Conversational AI Memory Writer
Intercepts chat queries to dynamically update the Knowledge Graph without requiring forms.
"""

import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.config import OLLAMA_GENERATE_URL, TEXT_MODEL
from app.core.dpp_extractor import check_ollama, clean_json_response
from app.core.passport_store import PassportStore

def analyze_write_intent(query: str, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Analyzes the user's chat query to determine if they are trying to WRITE or UPDATE
    the AI Household Memory (e.g., adding a product, logging maintenance).
    Returns a structured intent JSON or None if it's just a read query.
    """
    info = check_ollama()
    if not info.get("online") or not info.get("has_text_model"):
        return None

    model_to_use = info.get("chat_model") or TEXT_MODEL

    inventory = []
    for p in products:
        inventory.append({
            "passport_id": p.get("passport_id"),
            "product": p.get("product"),
            "brand": p.get("brand"),
            "model": p.get("model")
        })

    prompt = f"""
You are the AI Household Memory Engine. Your job is to detect if the user is trying to ADD a new product or LOG a maintenance event into their household registry.
Today's date is: {datetime.now().strftime('%Y-%m-%d')}

USER QUERY: "{query}"

EXISTING INVENTORY:
{json.dumps(inventory, indent=2)}

Determine if the user's query is a WRITE intent. 
If it is a general question (e.g., "when does my warranty expire?" or "what do I have?"), return {{"intent": "none"}}.
If they are actively adding a new product they bought, return:
{{
  "intent": "add_product",
  "product": "Product Name",
  "brand": "Brand Name",
  "purchase_price": 12345,
  "currency": "INR",
  "purchase_date": "YYYY-MM-DD"
}}
If they are actively logging an event (maintenance, filter change, repair) on an existing product, find the matching passport_id from EXISTING INVENTORY and return:
{{
  "intent": "log_event",
  "passport_id": "PP-xxx",
  "event_type": "service", 
  "description": "Short description of what was done",
  "date": "YYYY-MM-DD"
}}
Note: event_type must be one of: "service", "consumable", "installation".

Respond ONLY with valid JSON. No markdown, no explanation.
"""
    try:
        from app.config import ASK_LLM_TIMEOUT
        res = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0},
            },
            timeout=ASK_LLM_TIMEOUT,
        )
        if res.status_code == 200:
            text = res.json().get("response", "").strip()
            # Clean markdown code blocks if any
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            parsed = json.loads(text)
            if parsed and parsed.get("intent") in ["add_product", "log_event"]:
                return parsed
    except Exception as e:
        print(f"[MemoryWriter] LLM Parsing Error: {e}")
        return None
    return None

def execute_memory_update(intent: Dict[str, Any], store: PassportStore) -> Dict[str, Any]:
    """
    Executes the structured write intent onto the passport store.
    Returns the confirmation response for the chat.
    """
    if intent["intent"] == "add_product":
        new_passport = {
            "product": intent.get("product", "Unknown Product"),
            "brand": intent.get("brand", "Unknown Brand"),
            "purchase_price": intent.get("purchase_price"),
            "currency": intent.get("currency", "INR"),
            "purchase_date": intent.get("purchase_date", datetime.now().strftime("%Y-%m-%d")),
            "events": [
                {"type": "purchase", "date": intent.get("purchase_date", datetime.now().strftime("%Y-%m-%d")), "description": "Added via Conversational AI Memory"}
            ]
        }
        stored = store.add_passport(new_passport, source="chat_memory", auto_link=False)
        brand = stored["passport"].get("brand")
        prod = stored["passport"].get("product")
        price = stored["passport"].get("purchase_price")
        price_str = f" for {intent.get('currency', 'INR')} {price}" if price else ""
        return {
            "answer": f"I have committed this to memory! Added your new **{brand} {prod}**{price_str} to the Household Registry.",
            "sources": [{"title": "Conversational Memory Update", "field": "New Product", "confidence": "high"}],
            "confidence": "high",
            "why": "Extracted add_product intent from your message.",
            "intent": "memory_write",
            "suggestions": ["Show all registered products", "What needs my attention this month?"]
        }

    elif intent["intent"] == "log_event":
        pid = intent.get("passport_id")
        passport = store.get_by_id(pid)
        if not passport:
            return {
                "answer": "I tried to log that event, but I couldn't confidently match it to a specific product in your registry. Could you specify which appliance?",
                "sources": [],
                "confidence": "low",
                "why": "Target passport_id not found in store.",
                "intent": "memory_write_failed",
                "suggestions": ["Show all registered products"]
            }

        if "events" not in passport:
            passport["events"] = []

        new_event = {
            "type": intent.get("event_type", "service"),
            "date": intent.get("date", datetime.now().strftime("%Y-%m-%d")),
            "description": intent.get("description", "Logged via Conversational AI Memory")
        }
        passport["events"].append(new_event)
        
        # Save back to store
        store.update(pid, {"events": passport["events"]})
        
        return {
            "answer": f"Memory updated. I logged the **{new_event['type']}** event for your **{passport.get('brand')} {passport.get('product')}**.",
            "sources": [{"title": f"{passport.get('brand')} {passport.get('product')} Service Log", "field": "events", "confidence": "high"}],
            "confidence": "high",
            "why": f"Extracted log_event intent and appended to {pid}.",
            "intent": "memory_write",
            "suggestions": ["Show service history for this product", "What needs my attention this month?"]
        }

    return {"answer": "Intent not recognized as a valid write operation."}
