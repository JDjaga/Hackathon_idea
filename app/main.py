"""
AI Product Guardian — Master FastAPI Application
Mounts all REST API routers, static assets, HTML templates, and serves the Web Dashboard.
"""

import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import (
    STATIC_DIR,
    TEMPLATES_DIR,
    SERVER_HOST,
    SERVER_PORT,
    YOLO_MODEL_PATH
)
from app.api import dpp_router, matcher_router, detector_router, samples_router
from app.core.dpp_extractor import check_ollama
from app.core.ocr_engine import is_ocr_available
from app.core.passport_store import get_passport_store

# Initialize FastAPI Application
app = FastAPI(
    title="AI Product Guardian",
    description="Digital Product Passport (DPP) & Product Identity Verification Engine",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets & Templates
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount API Routers
app.include_router(dpp_router)
app.include_router(matcher_router)
app.include_router(detector_router)
app.include_router(samples_router)

store = get_passport_store()


@app.get("/api/health")
async def health_check():
    """Diagnostic health check for Ollama, OCR, YOLO, and Passport Store."""
    ollama_status = check_ollama()
    ocr_status = is_ocr_available()
    yolo_status = os.path.isfile(YOLO_MODEL_PATH)
    stats = store.stats()

    return {
        "status": "healthy",
        "service": "AI Product Guardian",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "diagnostics": {
            "ollama_online": ollama_status["online"],
            "has_vision_model": ollama_status["has_vision_model"],
            "vision_model": ollama_status["vision_model"],
            "tesseract_ocr_available": ocr_status,
            "yolo_model_loaded": yolo_status
        },
        "registry_stats": stats
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Serve the single-page interactive AI Product Guardian Web Dashboard."""
    ollama_status = check_ollama()
    ocr_status = is_ocr_available()
    yolo_status = os.path.isfile(YOLO_MODEL_PATH)
    stats = store.stats()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "stats": stats,
            "diagnostics": {
                "ollama": ollama_status["online"],
                "vision": ollama_status["has_vision_model"],
                "ocr": ocr_status,
                "yolo": yolo_status
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    print("=" * 65)
    print("  AI PRODUCT GUARDIAN — MASTER SERVER")
    print(f"  Web Dashboard & API: http://{SERVER_HOST}:{SERVER_PORT}")
    print("=" * 65)
    uvicorn.run("app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
