from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import PatronCreate, PatronResponse, PatronCreateResponse
from datetime import timedelta
from auth import CurrentEmployee
router = APIRouter()

@router.post(
    "/register",
    response_model=PatronCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_patron(patron:PatronCreate, current_employee:CurrentEmployee, db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to register a patron"
        )
    

    result = await db.execute(
        select(models.Patron)
        .where(models.Patron.email == patron.email)
    )

    existing_patron = result.scalars().first()

    if existing_patron:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A patron with the same email already exist"
        )
    
    new_patron = models.Patron(**patron.model_dump())

    db.add(new_patron)
    await db.commit()
    await db.refresh(new_patron)
    return new_patron

