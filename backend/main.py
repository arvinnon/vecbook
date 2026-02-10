from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware 
from database.db import create_tables

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
     allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(core_router)
app.include_router(teachers_router)
app.include_router(attendance_router)
app.include_router(training_router)
app.include_router(admin_router)
