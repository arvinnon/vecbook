from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware 
from backend.config import (
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_ORIGINS,
)
from database.db import create_tables

from backend.routers.auth import router as auth_router
from backend.routers.admin import router as admin_router
from backend.routers.attendance import router as attendance_router
from backend.routers.core import router as core_router
from backend.routers.teachers import router as teachers_router
from backend.routers.training import router as training_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Vecbook API", lifespan=lifespan)

# -----------------------------
# CORS (React dev server)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)


app.include_router(core_router)
app.include_router(auth_router)
app.include_router(teachers_router)
app.include_router(attendance_router)
app.include_router(training_router)
app.include_router(admin_router)
