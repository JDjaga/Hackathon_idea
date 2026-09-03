import requests, json
from app.core.dpp_extractor import check_ollama, clean_json_response

model = check_ollama().get("chat_model") or "qwen2.5:3b"

prompt = """You are the AI Household Memory Engine. Your job is to detect if the user is trying to ADD a new product or LOG a maintenance event into their household registry.
Today's date is: 2026-09-03
USER QUERY: "I bought a new Dyson Vacuum Cleaner today for 45000 INR"
EXISTING INVENTORY: []
Determine if the user's query is a WRITE intent. 
If it is a general question (e.g., "when does my warranty expire?" or "what do I have?"), return {"intent": "none"}.
If they are actively adding a new product they bought, return:
{
  "intent": "add_product",
  "product": "Product Name",
  "brand": "Brand Name",
  "purchase_price": 12345,
  "currency": "INR",
  "purchase_date": "YYYY-MM-DD"
}
Respond ONLY with valid JSON. No markdown, no explanation."""

try:
    r = requests.post("http://127.0.0.1:11434/api/generate", json={"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.0}})
    text = r.json().get("response")
    print("LLM returned:", text)
    parsed = clean_json_response(text)
    print("Parsed:", parsed)
except Exception as e:
    print("Error:", e)
