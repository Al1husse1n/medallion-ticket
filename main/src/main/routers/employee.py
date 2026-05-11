from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import EmployeeCreate, EmployeeResponse
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from auth import(
    create_access_token,
    hash_password,
    CurrentEmployee,
    verify_password
)
from config import settings

router = APIRouter()

@router.post(
    '/register',
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_employee(employee: EmployeeCreate, current_employee: CurrentEmployee, db: Annotated[AsyncSession, Depends(get_db)]):
    if current_employee.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your unauthorized to register an employee"
        )
    
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == employee.email.lower())
    )

    existing_employee = result.scalars().first()

    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this email already exists"
        )
    
    new_employee = models.Employee(
        full_name = employee.full_name,
        email = employee.email,
        password_hash = hash_password(employee.password),
        role = employee.role or models.Role.CLERK
    )

    if employee.joined_at:
        new_employee.joined_at = employee.joined_at

    db.add(new_employee)
    await db.commit()
    await db.refresh(new_employee)

    return new_employee


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse
)
async def get_employee(employee_email:str, current_employee: CurrentEmployee, db:Annotated[AsyncSession, Depends(get_db)]):
    if current_employee.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your unauthorized to view employee data"
        )
    
    result = await db.execute(
        select(models.Employee)
        .where(func.lower(models.Employee.email) == employee_email.lower())
        .options(selectinload(models.Employee.tickets_sold))
    )

    employee = result.scalars().first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is no employee with this email"
        )
    
    return employee         


