from fastapi import FastAPI
from sqlalchemy import select 
from database import Base, engine, get_db
from contextlib import asynccontextmanager  
from sqlalchemy.orm import selectinload

from routers import employee, patron


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

medallion = FastAPI(lifespan=lifespan)

medallion.include_router(employee.router, prefix="/medallion/employee", tags=["employee"])
medallion.include_router(patron.router, prefix="/medallion/patron", tags=["patron"])