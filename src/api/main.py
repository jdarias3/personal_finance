from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import structlog

from src.api.pages import router as pages_router
from src.api.pages_debts import router as debts_router
from src.api.auth import router as auth_router, get_current_user
from src.api.templates import setup_jinja_env
from src.infrastructure.database import async_session_maker, engine

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

app = FastAPI(title="Clarity - Personal Finance OS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent.parent / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

setup_jinja_env(app)

@app.middleware("http")
async def add_user_context(request: Request, call_next):
    async with async_session_maker() as db:
        user = await get_current_user(request, db)
        request.state.user = user
    response = await call_next(request)
    return response

app.include_router(pages_router)
app.include_router(debts_router)
app.include_router(auth_router)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()