from __future__ import annotations
from typing import Optional
# title: Optional[str] = Field(None, min_length=1, max_length=100)
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from decimal import Decimal
from models import SeatCategory, TicketStatus, Role


class EmployeeBase(BaseModel):
    role: Role
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=100)
    joined_at: Optional[datetime] = Field(
        None,
        description="When the employee started at the company"
    )

class EmployeeCreate(EmployeeBase):
    password: str = Field(min_length=8)

class EmployeeRegisterResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int 

class EmployeeResponse(EmployeeRegisterResponse):
    tickets_sold: list[TicketResponse] = []


class PatronBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=100)

class PatronCreate(PatronBase):
    pass

class PatronCreateResponse(PatronBase):
    id: int
    created_at: datetime

class PatronResponse(PatronCreateResponse):
    is_deleted: bool
    tickets: list[TicketResponse] = []       


class ProductionBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: str = Field(min_length=1, max_length=50)

class ProductionCreate(ProductionBase):
    pass

class ProductionCreateResponse(ProductionBase):
    id: int

class ProductionResponse(ProductionCreateResponse):
    performances: list[PerformanceResponse] = []

class PerformanceBase(BaseModel):
    performance_datetime: datetime = Field(description="Date and time of the performance")


class PerformanceCreate(PerformanceBase):
    production_id: int

class PerformanceCreateResponse(PerformanceBase):
    production: ProductionResponse

class PerformanceResponse(PerformanceCreateResponse):
    tickets: list[TicketResponse] = []


class SeatBase(BaseModel):
    seat_row: str
    seat_number: int
    category: str

class SeatResponse(SeatBase):
    id: int
    ticket_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class SeatBulkCreateResponse(BaseModel):
    message: str
    total_seats: int
    vip_seats: int
    premium_seats: int
    regular_seats: int

class TicketBase(BaseModel):
    price: Decimal
    patron_id: int
    performance_id: int
    seat_id: int

class TicketCreate(TicketBase):
    pass

class TicketCreateResponse(TicketBase):
    id: int
    status: str
    clerk_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class TicketResponse(BaseModel):
    id: int
    price: Decimal
    status: str
    patron_id: int
    performance_id: int
    seat_id: int
    clerk_id: int
    created_at: datetime
    buyer: Optional[dict] = None
    performance: Optional[dict] = None
    seat: Optional[dict] = None
    seller: Optional[dict] = None
    
    class Config:
        from_attributes = True
        
class Token(BaseModel):
    access_token: str
    token_type: str

class CursorParams(BaseModel):
    cursor: Optional[int] = None
    limit: int = 5

class PaginatedResponse(BaseModel):
    items: list[PatronResponse]
    next_cursor: Optional[int]
    has_next: bool
    limit: int

