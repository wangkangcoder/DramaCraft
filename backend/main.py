from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.core.local_runtime import start_monitor


app = FastAPI(
    title="AI Screenplay System API",
    description="Local API and static app server for the screenplay system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def startup_local_runtime_monitor():
    start_monitor()


@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/ai-screenplay-system/")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount(
        "/ai-screenplay-system",
        StaticFiles(directory=frontend_dist, html=True),
        name="frontend",
    )
