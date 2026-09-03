import os
import time
import requests
import sys

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import OLLAMA_GENERATE_URL, YOLO_MODEL_PATH
from app.core.dpp_extractor import check_ollama
from app.core.ocr_engine import is_ocr_available, get_ocr_engine_name
from app.core.product_detector import detect_appliances

def run_tests():
    results = []
    results.append("# AI Models Test Results\n")
    results.append(f"**Date Executed**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Test Ollama
    results.append("## 1. Ollama LLM")
    try:
        ollama_info = check_ollama()
        if ollama_info.get("online"):
            results.append("✅ **Ollama Service**: ONLINE")
            
            # Identify model
            model = ollama_info.get("chat_model") or ollama_info.get("vision_model") or "qwen2.5:0.5b"
            results.append(f"✅ **Active Model Detected**: `{model}`")
            
            # Test Inference
            start_time = time.time()
            prompt = "Respond with exactly the word: SUCCESS"
            res = requests.post(
                OLLAMA_GENERATE_URL,
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
                timeout=15.0
            )
            elapsed = time.time() - start_time
            if res.status_code == 200:
                response_text = res.json().get("response", "").strip()
                results.append(f"✅ **Inference Test**: Passed (Response: '{response_text}') in {elapsed:.2f}s")
            else:
                results.append(f"❌ **Inference Test**: Failed with status code {res.status_code}")
                
        else:
            results.append("❌ **Ollama Service**: OFFLINE or UNREACHABLE")
    except Exception as e:
        results.append(f"❌ **Ollama Service**: Error occurred - {e}")
        
    # 2. Test OCR Engine
    results.append("\n## 2. OCR Engine")
    try:
        if is_ocr_available():
            engine_name = get_ocr_engine_name()
            results.append(f"✅ **OCR Engine**: ONLINE (`{engine_name}`)")
        else:
            results.append("❌ **OCR Engine**: OFFLINE or NOT INSTALLED")
    except Exception as e:
        results.append(f"❌ **OCR Engine**: Error occurred - {e}")
        
    # 3. Test YOLO Model
    results.append("\n## 3. YOLO Object Detection")
    try:
        if os.path.exists(YOLO_MODEL_PATH):
            results.append(f"✅ **YOLO Model File**: FOUND (`{os.path.basename(YOLO_MODEL_PATH)}`)")
            # We can't easily test inference without a dummy image, but we can verify it loads
            try:
                from ultralytics import YOLO
                model = YOLO(YOLO_MODEL_PATH)
                results.append("✅ **YOLO Model Loading**: SUCCESS")
            except Exception as e:
                results.append(f"❌ **YOLO Model Loading**: FAILED - {e}")
        else:
            results.append(f"❌ **YOLO Model File**: NOT FOUND at `{YOLO_MODEL_PATH}`")
    except Exception as e:
        results.append(f"❌ **YOLO Engine**: Error occurred - {e}")

    # Write results to file
    output_path = "ai_model_test_results.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    print(f"Test results saved to {output_path}")

if __name__ == "__main__":
    print("Running comprehensive AI models test...")
    run_tests()
