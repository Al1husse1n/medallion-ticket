from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, UTC, time
import models
from database import get_db
from schema import PerformanceCreate, PerformanceCreateResponse, PerformanceResponse
from auth import CurrentEmployee

router = APIRouter()


@router.post("/register", response_model=PerformanceCreateResponse, status_code=201)
async def register_performance(
    performance: PerformanceCreate,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "You are not authorized to register a performance")
    
    # Check for performances within 4 hours (same production)
    time_window = timedelta(hours=4)
    start_window = performance.performance_datetime - time_window
    end_window = performance.performance_datetime + time_window
    
    result = await db.execute(
        select(models.Performance)
        .where(
            models.Performance.production_id == performance.production_id,
            models.Performance.performance_datetime.between(start_window, end_window)
        )
    )
    existing_performance = result.scalars().first()
    
    if existing_performance:
        raise HTTPException(400, f"A performance already exists within 4 hours of this time.")
    
    new_performance = models.Performance(**performance.model_dump())
    db.add(new_performance)
    await db.commit()
    await db.refresh(new_performance)
    return new_performance


@router.get("/performance_date", response_model=List[PerformanceResponse])
async def get_performances_by_date(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)],
    performance_date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "You are not authorized to search performances")
    
    try:
        search_date = datetime.strptime(performance_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    start_of_day = datetime.combine(search_date, time.min, tzinfo=UTC)
    end_of_day = datetime.combine(search_date + timedelta(days=1), time.min, tzinfo=UTC)

    # ✅ Complete nested eager loading
    result = await db.execute(
        select(models.Performance)
        .where(
            models.Performance.performance_datetime >= start_of_day,
            models.Performance.performance_datetime < end_of_day
        )
        .options(
            selectinload(models.Performance.production),
            selectinload(models.Performance.tickets)
            .selectinload(models.Ticket.buyer),
            selectinload(models.Performance.tickets)
            .selectinload(models.Ticket.seat),
        )
        .order_by(models.Performance.performance_datetime)
    )
    
    performances = result.scalars().all()
    
    if not performances:
        raise HTTPException(404, f"No performances found on {search_date}")
    
    return performances


@router.get("/", response_model=List[PerformanceResponse])
async def list_performances(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)],
    future: bool = Query(False, description="Return only future performances")
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "You are not authorized to view performances")

    query = select(models.Performance).options(
        selectinload(models.Performance.production),
        selectinload(models.Performance.tickets)
        .selectinload(models.Ticket.buyer),
        selectinload(models.Performance.tickets)
        .selectinload(models.Ticket.seat),
    )

    if future:
        now_utc = datetime.now(UTC)
        query = query.where(models.Performance.performance_datetime >= now_utc)

    query = query.order_by(models.Performance.performance_datetime)

    result = await db.execute(query)
    performances = result.scalars().all()

    return performances


@router.delete("/{performance_id}", response_model=PerformanceResponse, status_code=200)
async def delete_performance(
    performance_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role != models.Role.MANAGER:
        raise HTTPException(403, "Only managers can delete performances")
    
    result = await db.execute(
        select(models.Performance)
        .where(models.Performance.id == performance_id)
        .options(
            selectinload(models.Performance.production),
            selectinload(models.Performance.tickets)
        )
    )

    performance = result.scalars().first()

    if not performance:
        raise HTTPException(404, "No performance was found with that ID")
    
    # Check for sold tickets
    sold_tickets = [t for t in performance.tickets if t.status == models.TicketStatus.SOLD]
    if sold_tickets:
        raise HTTPException(400, f"Cannot delete performance with {len(sold_tickets)} sold tickets")
    
    await db.delete(performance)
    await db.commit()
    
    return performance