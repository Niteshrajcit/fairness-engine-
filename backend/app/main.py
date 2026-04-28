from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.upload import router as upload_router
from app.routes.analyze import router as analyze_router
from app.routes.simulate import router as simulate_router
from app.routes.strategy import router as strategy_router
from app.routes.stream import router as stream_router
from app.routes.sessions import router as sessions_router

app = FastAPI(title="Conversational Fairness Intelligence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(analyze_router, prefix="/api", tags=["analyze"])
app.include_router(simulate_router, prefix="/api", tags=["simulate"])
app.include_router(strategy_router, prefix="/api", tags=["strategy"])
app.include_router(stream_router, prefix="/api", tags=["stream"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}
