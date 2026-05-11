from __future__ import annotations
from typing import Optional
# title: Optional[str] = Field(None, min_length=1, max_length=100)
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
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
    id: int
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=100)

class PatronCreate(PatronBase):
    pass

class PatronCreateResponse(PatronBase):
    created_at: datetime

class PatronResponse(PatronCreateResponse):
    is_deleted: bool
    tickets: list[TicketResponse] = []

class TicketBase(BaseModel):
    pass
class TicketResponse(TicketBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

