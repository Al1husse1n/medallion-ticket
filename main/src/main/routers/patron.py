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

@router.get(
    "/{patron_email}",
    response_model=PatronResponse
)

async def get_patron_data(patron_email:str, current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to get patron data"
        )  
    
    result = await db.execute(
        select(models.Patron)
        .where(func.lower(models.Patron.email) == patron_email.lower())
        .options(selectinload(models.Patron.tickets))
    )

    patron = result.scalars().first()

    if not patron or patron.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patron exist with this email"
        )
    
    return patron


@router.get(
    "/",
    response_model=list[PatronResponse]
)
async def get_patron(current_employee:CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to get patron list"
        )
    
    result = await db.execute(
        select(models.Patron)
        .where(models.Patron.is_deleted == True)
        .options(selectinload(models.Patron.tickets))
    
    )

    patrons = result.scalars().all()
    
    return patrons

@router.delete(
    "/{patron_email}",
    response_model=PatronResponse
)
async def delete_patron(patron_email:str, current_employee:CurrentEmployee, db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()

    if not employee or employee.role !=  "clerk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete a patron"
        )  

    result = await db.execute(
        select(models.Patron)
        .where(func.lower(models.Patron.email) == patron_email.lower())
        .options(selectinload(models.Patron.tickets))
    )

    patron = result.scalars().first()

    if not patron:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patron exist with this email"
        )

    if patron.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patron is already deleted"
        )  
    
    patron.is_deleted = True
    await db.commit()
    await db.refresh(patron)
    return patron
    
