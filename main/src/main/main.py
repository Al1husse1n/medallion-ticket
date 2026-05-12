from fastapi import FastAPI
from sqlalchemy import select 
from database import Base, engine, get_db
from contextlib import asynccontextmanager  
from sqlalchemy.orm import selectinload

from routers import employee, patron, production, performance, seat, ticket


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

medallion = FastAPI(lifespan=lifespan)

medallion.include_router(employee.router, prefix="/medallion/employee", tags=["employee"])
medallion.include_router(patron.router, prefix="/medallion/patron", tags=["patron"])
medallion.include_router(production.router, prefix="/medallion/production", tags=["production"])
medallion.include_router(performance.router, prefix="/medallion/performance", tags=["performance"])
medallion.include_router(seat.router, prefix="/medallion/seat", tags=["seat"])
medallion.include_router(ticket.router, prefix="/medallion/ticket", tags=["ticket"])