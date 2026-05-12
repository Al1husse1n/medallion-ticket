from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import ProductionCreate, ProductionCreateResponse, ProductionResponse
from auth import CurrentEmployee

router = APIRouter()

@router.post(
    "/register",
    response_model=ProductionCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_production(production:ProductionCreate, current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to register a production"
        )
    
    new_production = models.Production(**production.model_dump())
    db.add(new_production)
    await db.commit()
    await db.refresh(new_production)
    return new_production

@router.get(
    "/",
    response_model=list[ProductionResponse]
)
async def get_productions(current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view production list"
        )
    
    result = await db.execute(
        select(models.Production)
        .options(selectinload(models.Production.performances))
        .order_by(models.Production.name)
    )

    productions = result.scalars().all()

    return productions



@router.delete(
    "/{production_id}",
    response_model=ProductionResponse
)
async def delete_production(production_id:int, current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete a production"
        )
    
    result = await db.execute(
        select(models.Production)
        .where(models.Production.id == production_id)
        .options(selectinload(models.Production.performances))
    )

    production = result.scalars().first()

    if not production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="there is no production with this ID"
        )

    await db.delete(production)
    await db.commit()

    return production


@router.get(
    "/{production_name}",
    response_model=list[ProductionResponse]
)
async def search_production(production_name:str, current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to search up production"
        )
    
    result = await db.execute(
        select(models.Production)
        .where(func.lower(models.Production.name) == production_name.lower())
        .options(selectinload(models.Production.performances))
    )

    production = result.scalars().all()
    if not production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There is no production with that name"
        )
    
    return production