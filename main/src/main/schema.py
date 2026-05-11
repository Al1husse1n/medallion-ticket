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
    tickets_sold: list[TicketResponse] = None



class TicketBase(BaseModel):
    pass
class TicketResponse(TicketBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

