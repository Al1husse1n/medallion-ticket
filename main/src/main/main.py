from fastapi import FastAPI
from sqlalchemy import select 
from database import Base, engine, get_db
from contextlib import asynccontextmanager  
from sqlalchemy.orm import selectinload
from fastapi.middleware.cors import CORSMiddleware
from routers import employee, patron, production, performance, seat, ticket


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

medallion = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",      # React dev server
    "http://localhost:3001",      # Alternative React port
    "http://localhost:5173",      # Vite dev server
    "http://localhost:8000",      # Same origin
    "http://127.0.0.1:3000",      # Localhost with IP
    "http://127.0.0.1:5173",      # Vite with IP
    "http://localhost:5500",      # Live Server (VS Code)
    "http://127.0.0.1:5500",      # Live Server IP
]


medallion.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # List of allowed origins
    allow_credentials=True,           # Allow cookies and authorization headers
    allow_methods=["*"],              # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],              # Allow all headers
    expose_headers=["*"],             # Expose all headers to the frontend
    max_age=3600,                     # Cache preflight requests for 1 hour
)

medallion.include_router(employee.router, prefix="/medallion/employee", tags=["employee"])
medallion.include_router(patron.router, prefix="/medallion/patron", tags=["patron"])
medallion.include_router(production.router, prefix="/medallion/production", tags=["production"])
medallion.include_router(performance.router, prefix="/medallion/performance", tags=["performance"])
medallion.include_router(seat.router, prefix="/medallion/seat", tags=["seat"])
medallion.include_router(ticket.router, prefix="/medallion/ticket", tags=["ticket"])