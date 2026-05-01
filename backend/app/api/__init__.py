from fastapi import APIRouter

from app.api import ai, auth, fingerprint, narrative, runtime


router = APIRouter()
router.include_router(narrative.router, prefix="/narrative", tags=["narrative"])
router.include_router(fingerprint.router, prefix="/fingerprint", tags=["fingerprint"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(runtime.router, prefix="/runtime", tags=["runtime"])
