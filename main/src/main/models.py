from __future__ import annotations          #this import was added after the forward referencing (no need for them anymore)
from typing import Optional
from decimal import Decimal
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Numeric, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


from database import Base

class SeatCategory(str, Enum):
    VIP = "vip"
    REGULAR = "regular"

class TicketStatus(str, Enum):
    SOLD = "sold"
    CANCELLED = "cancelled"

class Role(str, Enum):
    CLERK = "clerk"
    MANAGER = "manager"


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[Role] = mapped_column(
        SQLAlchemyEnum(Role, create_constraint=True, validate_string=True),
        default= Role.CLERK
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    tickets_sold: Mapped[list["Ticket"]] = relationship(back_populates="seller")            #"Ticket" is in string because we haveb't defined Ticket class yet(Forward referencing)
    

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
        server_default=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False  
    )
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="buyer")

class Production(Base):
    __tablename__ = "productions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    performances: Mapped[list["Performance"]] = relationship(back_populates="production")             #to use production.performances


class Performance(Base):
    __tablename__ = "performances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    performance_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True          
    )

    production_id:Mapped[int] = mapped_column(
        ForeignKey("productions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    production: Mapped[Production] = relationship(back_populates="performances") 
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="performance")   


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
        ),
    )

    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="seat", uselist=False)       #uselist for one to one r/ship,  
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
        ForeignKey("patrons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    performance_id: Mapped[int] = mapped_column(
        ForeignKey("performances.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    seat_id: Mapped[int] = mapped_column(           #means cancelled tickets cant be bought again unless deleted first from the table
        ForeignKey("seats.id", ondelete="CASCADE"),
        nullable=False
    )
    clerk_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    buyer: Mapped[Patron] = relationship(back_populates= "tickets")
    performance: Mapped[Performance] = relationship(back_populates="tickets")
    seat: Mapped[Seat] = relationship(back_populates="ticket")
    seller: Mapped[Employee] = relationship(back_populates="tickets_sold")

    __table_args__ = (
        UniqueConstraint(
            "performance_id", "seat_id",
            name="uq_performance_seat"          #prevents double booking    
        ),
    )
