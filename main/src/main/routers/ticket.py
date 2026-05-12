from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal
from datetime import datetime, UTC

import models
from database import get_db
from schema import TicketCreate, TicketResponse, TicketCreateResponse
from auth import CurrentEmployee

router = APIRouter()


# ==================== TICKET CREATION ====================

@router.post(
    "/create",
    response_model=TicketCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_ticket(
    ticket: TicketCreate,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Create a new ticket (sell a ticket to a patron)"""
    
    # Check authorization - only clerks and managers can sell tickets
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to sell tickets"
        )
    
    # Verify patron exists and is not deleted
    result = await db.execute(
        select(models.Patron)
        .where(
            models.Patron.id == ticket.patron_id,
            models.Patron.is_deleted == False
        )
    )
    patron = result.scalars().first()
    
    if not patron:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron not found or has been deleted"
        )
    
    # Verify performance exists and is in the future
    result = await db.execute(
        select(models.Performance)
        .where(models.Performance.id == ticket.performance_id)
    )
    performance = result.scalars().first()
    
    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performance not found"
        )
    
    if performance.performance_datetime < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sell tickets for past performances"
        )
    
    # Verify seat exists
    result = await db.execute(
        select(models.Seat)
        .where(models.Seat.id == ticket.seat_id)
    )
    seat = result.scalars().first()
    
    if not seat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seat not found"
        )
    
    # Check if seat is already taken for this performance
    result = await db.execute(
        select(models.Ticket)
        .where(
            models.Ticket.performance_id == ticket.performance_id,
            models.Ticket.seat_id == ticket.seat_id,
            models.Ticket.status != models.TicketStatus.CANCELLED
        )
    )
    existing_ticket = result.scalars().first()
    
    if existing_ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat {seat.seat_row}{seat.seat_number} is already booked for this performance"
        )
    
    # Create new ticket
    new_ticket = models.Ticket(
        price=ticket.price,
        status=models.TicketStatus.SOLD,
        patron_id=ticket.patron_id,
        performance_id=ticket.performance_id,
        seat_id=ticket.seat_id,
        clerk_id=current_employee.id
    )
    
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)
    
    # Load relationships for response
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.id == new_ticket.id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
    )
    ticket_with_relations = result.scalars().first()
    
    return ticket_with_relations


# ==================== TICKET RETRIEVAL ====================

@router.get(
    "/",
    response_model=List[TicketResponse]
)
async def get_all_tickets(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all tickets (authorized: clerk/manager)"""
    
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view ticket list"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
        .order_by(models.Ticket.created_at.desc())
    )
    
    tickets = result.scalars().all()
    
    return tickets


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse
)
async def get_ticket_by_id(
    ticket_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get a specific ticket by ID"""
    
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view ticket data"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.id == ticket_id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
    )
    
    ticket = result.scalars().first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ticket found with ID {ticket_id}"
        )
    
    return ticket


@router.get(
    "/by-patron/{patron_id}",
    response_model=List[TicketResponse]
)
async def get_tickets_by_patron(
    patron_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all tickets for a specific patron"""
    
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view ticket data"
        )
    
    # Verify patron exists
    result = await db.execute(
        select(models.Patron)
        .where(models.Patron.id == patron_id, models.Patron.is_deleted == False)
    )
    patron = result.scalars().first()
    
    if not patron:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron not found"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.patron_id == patron_id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
        .order_by(models.Ticket.created_at.desc())
    )
    
    tickets = result.scalars().all()
    
    return tickets


@router.get(
    "/by-performance/{performance_id}",
    response_model=List[TicketResponse]
)
async def get_tickets_by_performance(
    performance_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all tickets for a specific performance"""
    
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view ticket data"
        )
    
    # Verify performance exists
    result = await db.execute(
        select(models.Performance)
        .where(models.Performance.id == performance_id)
    )
    performance = result.scalars().first()
    
    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Performance not found"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.performance_id == performance_id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
        .order_by(models.Ticket.seat_id)
    )
    
    tickets = result.scalars().all()
    
    return tickets


@router.get(
    "/by-clerk/{clerk_id}",
    response_model=List[TicketResponse]
)
async def get_tickets_by_clerk(
    clerk_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all tickets sold by a specific clerk (manager only)"""
    
    # Only managers can view clerk-specific sales
    if current_employee.role != models.Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can view clerk sales data"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.clerk_id == clerk_id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
        .order_by(models.Ticket.created_at.desc())
    )
    
    tickets = result.scalars().all()
    
    return tickets


# ==================== TICKET CANCELLATION ====================

@router.post(
    "/{ticket_id}/cancel",
    response_model=TicketResponse
)
async def cancel_ticket(
    ticket_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Cancel a ticket"""
    
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel tickets"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.id == ticket_id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
    )
    
    ticket = result.scalars().first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ticket found with ID {ticket_id}"
        )
    
    if ticket.status == models.TicketStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket is already cancelled"
        )
    
    # Check if performance hasn't passed yet
    if ticket.performance.performance_datetime < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel tickets for past performances"
        )
    
    ticket.status = models.TicketStatus.CANCELLED
    await db.commit()
    await db.refresh(ticket)
    
    return ticket


# ==================== TICKET DELETION ====================

@router.delete(
    "/{ticket_id}",
    response_model=TicketResponse
)
async def delete_ticket(
    ticket_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Delete a ticket (permanent deletion, manager only)"""
    
    # Only managers can permanently delete tickets
    if current_employee.role != models.Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can permanently delete tickets"
        )
    
    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.id == ticket_id)
        .options(
            selectinload(models.Ticket.buyer),
            selectinload(models.Ticket.performance),
            selectinload(models.Ticket.seat),
            selectinload(models.Ticket.seller)
        )
    )
    
    ticket = result.scalars().first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ticket found with ID {ticket_id}"
        )
    
    # Store ticket info for response before deletion
    ticket_info = ticket
    
    await db.delete(ticket)
    await db.commit()
    
    return ticket_info