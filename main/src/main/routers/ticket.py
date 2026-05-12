from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal
from datetime import datetime, UTC

import models
from database import get_db
from schema import TicketCreate, TicketResponse, TicketCreateResponse, TicketUpdateStatus
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
    
    # Verify seat exists and is not already booked for this performance
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
    
    # Check if seat is already taken for this performance (unique constraint handles this too)
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


# ==================== TICKET STATUS UPDATE ====================

@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse
)
async def update_ticket_status(
    ticket_id: int,
    status_update: TicketUpdateStatus,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Update ticket status (e.g., cancel a ticket)"""
    
    if current_employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update ticket status"
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
    
    # Check if performance hasn't passed yet
    if ticket.performance.performance_datetime < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update tickets for past performances"
        )
    
    ticket.status = status_update.status
    await db.commit()
    await db.refresh(ticket)
    
    return ticket


@router.post(
    "/{ticket_id}/cancel",
    response_model=TicketResponse
)
async def cancel_ticket(
    ticket_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Cancel a ticket (refund)"""
    
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


# ==================== TICKET STATISTICS ====================

@router.get(
    "/stats/sales"
)
async def get_sales_statistics(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering")
):
    """Get sales statistics (manager only)"""
    
    if current_employee.role != models.Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can view sales statistics"
        )
    
    # Build date filter
    filters = []
    if start_date:
        filters.append(models.Ticket.created_at >= start_date)
    if end_date:
        filters.append(models.Ticket.created_at <= end_date)
    
    # Total tickets sold
    total_result = await db.execute(
        select(func.count(models.Ticket.id))
        .where(and_(*filters))
    )
    total_tickets = total_result.scalar()
    
    # Total revenue
    revenue_result = await db.execute(
        select(func.sum(models.Ticket.price))
        .where(and_(*filters))
    )
    total_revenue = revenue_result.scalar() or Decimal(0)
    
    # Sales by status
    sold_result = await db.execute(
        select(func.count(models.Ticket.id))
        .where(
            models.Ticket.status == models.TicketStatus.SOLD,
            and_(*filters)
        )
    )
    sold_count = sold_result.scalar()
    
    cancelled_result = await db.execute(
        select(func.count(models.Ticket.id))
        .where(
            models.Ticket.status == models.TicketStatus.CANCELLED,
            and_(*filters)
        )
    )
    cancelled_count = cancelled_result.scalar()
    
    # Average ticket price
    avg_result = await db.execute(
        select(func.avg(models.Ticket.price))
        .where(and_(*filters))
    )
    average_price = avg_result.scalar() or Decimal(0)
    
    # Sales by clerk
    clerk_sales_result = await db.execute(
        select(
            models.Employee.full_name,
            func.count(models.Ticket.id).label("tickets_sold"),
            func.sum(models.Ticket.price).label("revenue")
        )
        .join(models.Ticket, models.Employee.id == models.Ticket.clerk_id)
        .where(and_(*filters))
        .group_by(models.Employee.id, models.Employee.full_name)
        .order_by(func.sum(models.Ticket.price).desc())
    )
    clerk_sales = clerk_sales_result.all()
    
    return {
        "total_tickets_sold": total_tickets,
        "total_revenue": float(total_revenue),
        "average_ticket_price": float(average_price),
        "sold_count": sold_count,
        "cancelled_count": cancelled_count,
        "sales_by_clerk": [
            {
                "clerk_name": cs.full_name,
                "tickets_sold": cs.tickets_sold,
                "revenue": float(cs.revenue)
            }
            for cs in clerk_sales
        ]
    }