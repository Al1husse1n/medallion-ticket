from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from decimal import Decimal
from models import SeatCategory, TicketStatus, Role


# ==================== BRIEF RESPONSE MODELS (NO CIRCULAR REFERENCES) ====================

class PatronBriefResponse(BaseModel):
    """Patron without tickets (breaks circular reference)"""
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    is_deleted: bool
    
    class Config:
        from_attributes = True


class EmployeeBriefResponse(BaseModel):
    """Employee without tickets_sold (breaks circular reference)"""
    id: int
    full_name: str
    email: str
    role: str
    
    class Config:
        from_attributes = True


class ProductionBriefResponse(BaseModel):
    """Production without performances (breaks circular reference)"""
    id: int
    name: str
    type: str
    
    class Config:
        from_attributes = True


class PerformanceBriefResponse(BaseModel):
    """Performance without production and without tickets (breaks circular reference)"""
    id: int
    performance_datetime: datetime
    
    class Config:
        from_attributes = True


class SeatBriefResponse(BaseModel):
    """Seat without ticket (simple)"""
    id: int
    seat_row: str
    seat_number: int
    category: str
    
    class Config:
        from_attributes = True


# ==================== EMPLOYEE SCHEMAS ====================

class EmployeeBase(BaseModel):
    role: Role
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=100)
    joined_at: Optional[datetime] = None


class EmployeeCreate(EmployeeBase):
    password: str = Field(min_length=8)


class EmployeeRegisterResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int 


class EmployeeResponse(EmployeeRegisterResponse):
    tickets_sold: List["TicketResponse"] = []


# ==================== PATRON SCHEMAS ====================

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
    model_config = ConfigDict(from_attributes=True)


class PatronResponse(PatronCreateResponse):
    is_deleted: bool
    tickets: List["TicketResponse"] = []


# ==================== PRODUCTION SCHEMAS ====================

class ProductionBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: str = Field(min_length=1, max_length=50)


class ProductionCreate(ProductionBase):
    pass


class ProductionCreateResponse(ProductionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ProductionResponse(ProductionCreateResponse):
    performances: List[PerformanceBriefResponse] = []  # ✅ Brief version (no circular ref)


# ==================== PERFORMANCE SCHEMAS ====================

class PerformanceBase(BaseModel):
    performance_datetime: datetime = Field(description="Date and time of the performance")


class PerformanceCreate(PerformanceBase):
    production_id: int


class PerformanceCreateResponse(PerformanceBase):
    production: ProductionBriefResponse  # ✅ Brief version
    model_config = ConfigDict(from_attributes=True)


class PerformanceResponse(PerformanceCreateResponse):
    tickets: List["TicketResponse"] = []  # Full tickets for detail view


# ==================== SEAT SCHEMAS ====================

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


# ==================== TICKET SCHEMAS ====================

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
    buyer: Optional[PatronBriefResponse] = None      # ✅ Brief version (no tickets)
    performance: Optional[PerformanceBriefResponse] = None  # ✅ Brief version (no circular ref)
    seat: Optional[SeatBriefResponse] = None          # ✅ Brief version
    seller: Optional[EmployeeBriefResponse] = None    # ✅ Brief version (no tickets_sold)
    
    class Config:
        from_attributes = True


# ==================== AUTH SCHEMAS ====================

class Token(BaseModel):
    access_token: str
    token_type: str


# ==================== PAGINATION SCHEMAS ====================

class CursorParams(BaseModel):
    cursor: Optional[int] = None
    limit: int = 5


class PaginatedResponse(BaseModel):
    items: List[PatronResponse]
    next_cursor: Optional[int]
    has_next: bool
    limit: int


# ==================== FORWARD REFERENCE RESOLUTION ====================

EmployeeResponse.model_rebuild()
TicketResponse.model_rebuild()
PerformanceResponse.model_rebuild()
ProductionResponse.model_rebuild()
PatronResponse.model_rebuild()