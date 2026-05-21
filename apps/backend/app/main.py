from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, callback, files, jobs
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(callback.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
