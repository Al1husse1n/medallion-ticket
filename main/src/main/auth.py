from datetime import UTC, datetime, timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash              
from config import settings
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import models
from database import get_db

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="medallion/employee/token")       #where we get the token


def hash_password(password: str) -> str:            #during signup
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:     #during login
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes= settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})       
    encoded_jwt = jwt.encode(
        to_encode,      
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_access_token(token:str) -> str | None:
    """verify a jwt access token and return the subject(user_id) if valid"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options= {"require": ["exp", "sub"]},           #This tells jwt.decode() to require that the token contains both exp (expiration time) and sub (subject/user identifier) claims.
        )

    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.MissingRequiredClaimError as e:
        print(f"Token missing required claim: {e}")
        return None
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")
    

async def get_current_user(                             #for authorization  
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> models.User:
    
    user_id = verify_access_token(token=token)
    if user_id is None:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "invalid or expired token",
            headers= {"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "invalid or expired token",
            headers= {"WWW-Authenticate": "Bearer"}     
        )
    
    result = db.execute(select(models.User).where(models.User,id == user_id_int))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "User not found",
            headers= {"WWW-Authenticate": "Bearer"}
        )
    
    return user



CurrentUser = Annotated[models.User, Depends(get_current_user)] 