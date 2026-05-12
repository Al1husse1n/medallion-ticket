from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import ProductionCreate, ProductionCreateResponse, ProductionResponse
from auth import CurrentEmployee

router = APIRouter()


@router.post("/register", response_model=ProductionCreateResponse, status_code=201)
async def register_production(
    production: ProductionCreate,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to register a production")
    
    new_production = models.Production(**production.model_dump())
    db.add(new_production)
    await db.commit()
    await db.refresh(new_production)
    return new_production


@router.get("/", response_model=List[ProductionResponse])
async def get_all_productions(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to view production list")
    
    # ✅ Simpler eager loading - just load performances (no circular references)
    result = await db.execute(
        select(models.Production)
        .options(selectinload(models.Production.performances))
        .order_by(models.Production.name)
    )

    productions = result.scalars().all()
    return productions


@router.delete("/{production_id}", response_model=ProductionResponse)
async def delete_production(
    production_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role != models.Role.MANAGER:
        raise HTTPException(403, "Only managers can delete a production")
    
    result = await db.execute(
        select(models.Production)
        .where(models.Production.id == production_id)
        .options(selectinload(models.Production.performances))
    )

    production = result.scalars().first()

    if not production:
        raise HTTPException(404, f"There is no production with ID {production_id}")

    await db.delete(production)
    await db.commit()

    return production


@router.get("/{production_name}", response_model=List[ProductionResponse])
async def search_production(
    production_name: str,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to search for productions")
    
    result = await db.execute(
        select(models.Production)
        .where(func.lower(models.Production.name) == production_name.lower())
        .options(selectinload(models.Production.performances))
    )

    productions = result.scalars().all()
    
    if not productions:
        raise HTTPException(404, f"There is no production with name '{production_name}'")
    
    return productions