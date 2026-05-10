from __future__ import annotations
from decimal import Decimal
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Numeric, Float, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship


from database import Base

class SeatCategory(str, Enum):
    VIP = "vip"
    REGULAR = "regular"

class TicketStatus(str, Enum):
    SOLD = "sold"
    CANCELLED = "cancelled"

class Patron(Base):
    __tablename__ = "patrons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default= lambda: datetime.now(UTC)
    )

class Production(Base):
    __tablename__ = "productions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)


class Performance(Base):
    __tablename__ = "performances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    performance_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True          
    )

    production_id:Mapped[int] = mapped_column(
        ForeignKey("performances.id"),
        nullable=False,
        index=True
    )


class Seat(Base):       #hold seat until customer pays
    __tablename__ = "seats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seat_row: Mapped[str] = mapped_column(String(50), nullable=False)       #'A' through 'Z' etc.
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[SeatCategory] = mapped_column(
        SQLAlchemyEnum(SeatCategory, create_constraint=True, validate_string=True),
        default= SeatCategory.REGULAR
    )

    __table_args__ = (
        UniqueConstraint(
            "seat_row", "seat_number",
            name="uq_seatrow_seatnumber"
        )
    )

class Ticket(Base):
    __tablename__ = "tickets"
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    price: Mapped[Decimal] = mapped_column(
        Numeric(10,2),
        nullable= False 
    )
    status: Mapped[TicketStatus] = mapped_column(
        SQLAlchemyEnum(TicketStatus, create_constraint=True, validate_string=True),
        default= TicketStatus.SOLD
    )
    patron_id: Mapped[int] = mapped_column(
        ForeignKey("patrons.id"),
        nullable=False,
        index=True  
    )
    performance_id: Mapped[int] = mapped_column(
        ForeignKey("performances.id"),
        nullable=False,
        index=True
    )
    seat_id: Mapped[int] = mapped_column(
        ForeignKey("seats.id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default= lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "performance_id", "seat_id",
            name="uq_performance_seat"          #prevents double booking
        )
    )
