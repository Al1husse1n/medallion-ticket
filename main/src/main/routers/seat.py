from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import SeatResponse, SeatBulkCreateResponse
from auth import CurrentEmployee

router = APIRouter()

#one time seat initialization
@router.post(
    "/initialize",
    response_model=SeatBulkCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def initialize_seats(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Initialize the fixed seat inventory (602 seats: A1-Z24 with categories)"""
    
    # Fetch employee from database to check authorization
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()
    
    # Check authorization - only managers can initialize seats
    if not employee or employee.role != models.Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can initialize seat inventory"
        )
    
    # Check if seats already exist
    result = await db.execute(select(func.count(models.Seat.id)))
    seat_count = result.scalar()
    
    if seat_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seats already exist ({seat_count} seats). Cannot re-initialize."
        )
    
    # Generate 602 seats
    seats_to_create = []
    
    # Row letters A through Z (26 rows)
    rows = [chr(ord('A') + i) for i in range(26)]  # A, B, C, ..., Z
    
    # Seats per row: 24 seats (1-24) in some rows, fewer in others
    # Total target: 602 seats
    seats_per_row = {
        'A': 24, 'B': 24, 'C': 24, 'D': 24, 'E': 24, 'F': 24, 'G': 24, 'H': 24,
        'I': 24, 'J': 24, 'K': 23, 'L': 23, 'M': 23, 'N': 23, 'O': 23, 'P': 23,
        'Q': 22, 'R': 22, 'S': 22, 'T': 22, 'U': 22, 'V': 22, 'W': 21, 'X': 21,
        'Y': 21, 'Z': 21
    }
    
    # Category distribution based on row
    def get_category_for_seat(row: str, seat_num: int) -> models.SeatCategory:
        # VIP: Rows F-H, seats 5-15
        if row in ['F', 'G', 'H'] and 5 <= seat_num <= 15:
            return models.SeatCategory.VIP
        # Premium: Rows D-E, I-J, seats 1-24
        elif row in ['D', 'E', 'I', 'J']:
            return models.SeatCategory.PREMIUM
        # Regular: All other seats
        else:
            return models.SeatCategory.REGULAR
    
    total_seats = 0
    for row in rows:
        num_seats = seats_per_row.get(row, 20)
        for seat_num in range(1, num_seats + 1):
            category = get_category_for_seat(row, seat_num)
            seats_to_create.append(
                models.Seat(
                    seat_row=row,
                    seat_number=seat_num,
                    category=category
                )
            )
            total_seats += 1
    
    # Bulk insert all seats
    db.add_all(seats_to_create)
    await db.commit()
    
    # Get count by category for response
    vip_count = sum(1 for s in seats_to_create if s.category == models.SeatCategory.VIP)
    premium_count = sum(1 for s in seats_to_create if s.category == models.SeatCategory.PREMIUM)
    regular_count = sum(1 for s in seats_to_create if s.category == models.SeatCategory.REGULAR)
    
    return {
        "message": f"Successfully created {total_seats} seats",
        "total_seats": total_seats,
        "vip_seats": vip_count,
        "premium_seats": premium_count,
        "regular_seats": regular_count
    }




@router.get(
    "/",
    response_model=List[SeatResponse]
)
async def get_all_seats(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all seats (authorized: clerk/manager)"""
    
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()
    
    if not employee or employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view seat list"
        )
    
    result = await db.execute(
        select(models.Seat)
        .options(selectinload(models.Seat.ticket))
        .order_by(models.Seat.seat_row, models.Seat.seat_number)
    )
    
    seats = result.scalars().all()
    
    return seats


@router.get(
    "/by-category/{category}",
    response_model=List[SeatResponse]
)
async def get_seats_by_category(
    category: str,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get seats filtered by category (regular, vip, premium)"""
    
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()
    
    if not employee or employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view seat list"
        )
    
    # Validate category
    try:
        seat_category = models.SeatCategory(category.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Valid options: regular, vip, premium"
        )
    
    result = await db.execute(
        select(models.Seat)
        .where(models.Seat.category == seat_category)
        .options(selectinload(models.Seat.ticket))
        .order_by(models.Seat.seat_row, models.Seat.seat_number)
    )
    
    seats = result.scalars().all()
    
    if not seats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No seats found with category '{category}'"
        )
    
    return seats


@router.get(
    "/available",
    response_model=List[SeatResponse]
)
async def get_available_seats(
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get all seats that are not sold (no ticket associated)"""
    
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()
    
    if not employee or employee.role not in [models.Role.CLERK, models.Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view seat list"
        )
    
    # Get seats that have no ticket (left join where ticket.id is null)
    result = await db.execute(
        select(models.Seat)
        .outerjoin(models.Ticket, models.Seat.id == models.Ticket.seat_id)
        .where(models.Ticket.id == None)
        .options(selectinload(models.Seat.ticket))
        .order_by(models.Seat.seat_row, models.Seat.seat_number)
    )
    
    seats = result.scalars().all()
    
    return seats




@router.delete(
    "/{seat_id}",
    response_model=SeatResponse
)
async def delete_seat(
    seat_id: int,
    current_employee: CurrentEmployee,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Delete a seat (only if no associated ticket exists)"""
    
    # Fetch employee from database to check authorization
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == current_employee.email.lower())
    )
    employee = result.scalars().first()
    
    # Only managers can delete seats
    if not employee or employee.role != models.Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can delete seats"
        )
    
    # Get seat with ticket relationship
    seat_result = await db.execute(
        select(models.Seat)
        .where(models.Seat.id == seat_id)
        .options(selectinload(models.Seat.ticket))
    )
    
    seat = seat_result.scalars().first()
    
    if not seat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No seat found with ID {seat_id}"
        )
    
    # Check if seat has an associated ticket (sold or reserved)
    if seat.ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete seat {seat.seat_row}{seat.seat_number} because it has an associated ticket (ID: {seat.ticket.id})"
        )
    
    await db.delete(seat)
    await db.commit()
    
    return seat