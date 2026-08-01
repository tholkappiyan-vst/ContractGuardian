from fastapi import APIRouter
from app.api import auth, contracts, analysis, chat, comparison, ai_engine_routes, explainability

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(contracts.router, prefix="/contracts", tags=["Contracts"])
router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(comparison.router, prefix="/comparison", tags=["Comparison"])
router.include_router(ai_engine_routes.router, prefix="/engine", tags=["AI Engine"])
router.include_router(explainability.router, prefix="/explain", tags=["Explainability"])
