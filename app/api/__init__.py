"""
HomeMind — REST API Routers
"""

from app.api.routes_dpp import router as dpp_router
from app.api.routes_matcher import router as matcher_router
from app.api.routes_detector import router as detector_router
from app.api.routes_samples import router as samples_router
from app.api.routes_household import router as household_router
from app.api.routes_ask import router as ask_router

__all__ = ["dpp_router", "matcher_router", "detector_router", "samples_router", "household_router", "ask_router"]
