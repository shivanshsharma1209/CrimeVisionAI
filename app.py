import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import Config
from backend.models.database import engine, Base, SessionLocal
from backend.models.case import Case
from backend.routes.cases import cases_router
from backend.routes.evidence import evidence_router
from backend.routes.analysis import analysis_router
from backend.routes.chat import chat_router
from backend.routes.reports import reports_router
from backend.routes.system import system_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crimevision.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage directories exist
    Config.init_app(app)

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")

    # Seed demo case on startup if enabled and database is empty
    if Config.ENABLE_DEMO_MODE:
        db_sess = SessionLocal()
        try:
            if db_sess.query(Case).count() == 0:
                from backend.services.demo_service import DemoService
                try:
                    logger.info("Empty database detected. Seeding CV-DEMO-001 Warehouse Incident case...")
                    DemoService().seed_demo_case()
                except Exception as e:
                    logger.warning(f"Demo auto-seeding deferred: {e}")
        finally:
            db_sess.close()

    # Print a prominent banner after all startup tasks complete
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 56)
    print("  ✅ CrimeVision AI is RUNNING!")
    print(f"  🌐 Local:   http://127.0.0.1:{port}")
    print(f"  🌐 Network: http://0.0.0.0:{port}")
    print(f"  📄 API Docs: http://127.0.0.1:{port}/docs")
    print("=" * 56 + "\n")

    yield


app = FastAPI(
    title="CrimeVision AI",
    description="Intelligent Multimodal Forensic Analysis Platform",
    version="2.4",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Templates
templates = Jinja2Templates(directory="frontend/templates")

# Register routers
app.include_router(cases_router)
app.include_router(evidence_router)
app.include_router(analysis_router)
app.include_router(chat_router)
app.include_router(reports_router)
app.include_router(system_router)


# Frontend Main Entry Route
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# Global 404 handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": "Resource not found"}},
    )


# Global 500 handler
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting CrimeVision AI FastAPI server on http://127.0.0.1:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
