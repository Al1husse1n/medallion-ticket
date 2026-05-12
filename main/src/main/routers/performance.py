from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import models
from database import get_db
from schema import PerformanceCreate, PerformanceCreateResponse, PerformanceResponse
from auth import CurrentEmployee

router = APIRouter()

@router.post(
    "/register",
    response_model=PerformanceCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_performance(performance:PerformanceCreate, current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to register a performance"
        )
    
    time_window = timedelta(hours=4)
    start_window = performance.performance_datetime - time_window
    end_window = performance.performance_datetime + time_window
    
    result = await db.execute(
        select(models.Performance)
        .where(models.Performance.performance_datetime.between(start_window, end_window))
    )

    existing_performance = result.scalars().first()
    
    if existing_performance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A performance already exist at the same time"
        )
    
    new_performance = models.Performance(**performance.model_dump())
    db.add(new_performance)
    await db.commit()
    await db.refresh(new_performance)

    return new_performance

@router.get(
    "/performance_date",
    response_model=list[PerformanceResponse]
)
async def get_performance(
    current_employee:CurrentEmployee, 
    db: Annotated[AsyncSession, Depends(get_db)],
    performance_date: str = Query(..., description="Date in YYYY-MM-DD format")
    ):

    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to search up performance"
        )
    
    try:
        search_date = datetime.strptime(performance_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    result = await db.execute(
        select(models.Performance)
        .where(func.date(models.Performance.performance_datetime) == search_date)
        .options(selectinload(models.Performance.tickets), selectinload(models.Performance.production))
        .order_by(models.Performance.performance_datetime)
    )
    
    performances = result.scalars().all()
    
    if not performances:
        raise HTTPException(404, f"No performances found on {search_date}")
    
    return performances

@router.delete(
    "/{performance_id}",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK
)
async def delete_performance(performance_id:int, current_employee: CurrentEmployee, db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete a performance"
        )
    
    result = await db.execute(
        select(models.Performance)
        .where(models.Performance.id == performance_id)
        .options(selectinload(models.Performance.production), selectinload(models.Performance.tickets))
    )

    performance = result.scalars().first()

    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No performance was found with that ID"
        )
    
    await db.delete(performance)
    await db.commit()
    
    return performance