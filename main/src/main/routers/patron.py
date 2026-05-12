from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import PatronCreate, PatronResponse, PatronCreateResponse
from auth import CurrentEmployee

router = APIRouter()


@router.post("/register", response_model=PatronCreateResponse, status_code=201)
async def register_patron(
    patron: PatronCreate,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to register a patron")
    
    # Check if email exists
    result = await db.execute(
        select(models.Patron)
        .where(func.lower(models.Patron.email) == patron.email.lower())
    )
    if result.scalars().first():
        raise HTTPException(400, "A patron with the same email already exists")

    new_patron = models.Patron(**patron.model_dump())
    db.add(new_patron)
    await db.commit()
    await db.refresh(new_patron)
    return new_patron


@router.get("/{patron_email}", response_model=PatronResponse)
async def get_patron_data(
    patron_email: str,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to get patron data")
    
    result = await db.execute(
        select(models.Patron)
        .where(
            func.lower(models.Patron.email) == patron_email.lower(),
            models.Patron.is_deleted == False
        )
        .options(
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.buyer),
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.performance)
            .selectinload(models.Performance.production),
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.seat),
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.seller)
        )
    )
    
    patron = result.scalars().first()
    if not patron:
        raise HTTPException(404, "No patron exists with this email")
    
    return patron


@router.get("/", response_model=List[PatronResponse])
async def get_all_patrons(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to get patron list")
    
    # ✅ Complete nested eager loading for all patrons
    result = await db.execute(
        select(models.Patron)
        .where(models.Patron.is_deleted == False)
        .options(
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.buyer),
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.performance)
            .selectinload(models.Performance.production),
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.seat),
            selectinload(models.Patron.tickets)
            .selectinload(models.Ticket.seller)
        )
        .order_by(models.Patron.first_name)
    )
    
    patrons = result.scalars().all()
    return patrons


@router.delete("/{patron_email}", response_model=PatronResponse)
async def delete_patron(
    patron_email: str,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(403, "Not authorized to delete a patron")

    result = await db.execute(
        select(models.Patron)
        .where(func.lower(models.Patron.email) == patron_email.lower())
        .options(selectinload(models.Patron.tickets))
    )

    patron = result.scalars().first()
    if not patron:
        raise HTTPException(404, "No patron exists with this email")

    if patron.is_deleted:
        raise HTTPException(400, "Patron is already deleted")
    
    patron.is_deleted = True
    await db.commit()
    await db.refresh(patron)
    return patron