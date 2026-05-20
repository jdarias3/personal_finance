from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import structlog
import os
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from src.infrastructure.database import get_db
from src.domain.models import User, UserProfile

router = APIRouter()
logger = structlog.get_logger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

class TokenData(BaseModel):
    user_id: Optional[str] = None

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_password_hash(password: str) -> str:
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        if hasattr(request.state, 'user'):
            return request.state.user
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except:
        return None
    
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if user and not user.is_active:
        return None
    
    return user

@router.post("/api/register")
async def api_register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    from fastapi.responses import JSONResponse
    
    try:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            return JSONResponse(status_code=400, content={"detail": "Email already registered"})
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=name,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            profile_mode="financial-os"
        )
        db.add(profile)
        await db.commit()
        
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return JSONResponse(content={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "access_token": access_token,
            "token_type": "bearer"
        })
    except Exception as e:
        logger.error("api_register_error", error=str(e), email=email)
        return JSONResponse(status_code=500, content={"detail": "Registration failed"})

@router.post("/auth/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            return Response(
                content="<script>alert('Email already registered'); window.history.back();</script>",
                media_type="text/html",
                status_code=400
            )
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=name,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            profile_mode="financial-os"
        )
        db.add(profile)
        await db.commit()
        
        access_token = create_access_token(data={"sub": str(user.id)})
        
        response = Response(headers={"Location": "/onboarding"}, status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
    except Exception as e:
        logger.error("registration_error", error=str(e), email=email)
        return Response(
            content="<script>alert('Registration failed. Please try again.'); window.history.back();</script>",
            media_type="text/html",
            status_code=500
        )

@router.post("/api/login")
async def api_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    from fastapi.responses import JSONResponse
    
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            return JSONResponse(status_code=401, content={"detail": "Invalid email or password"})
        
        if not user.is_active:
            return JSONResponse(status_code=403, content={"detail": "Account is deactivated"})
        
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return JSONResponse(content={
            "access_token": access_token,
            "token_type": "bearer"
        })
    except Exception as e:
        logger.error("api_login_error", error=str(e), email=email)
        return JSONResponse(status_code=500, content={"detail": "Login failed"})

@router.post("/auth/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            return Response(
                content="<script>alert('Invalid email or password'); window.history.back();</script>",
                media_type="text/html",
                status_code=401
            )
        
        if not user.is_active:
            return Response(
                content="<script>alert('Account is deactivated'); window.history.back();</script>",
                media_type="text/html",
                status_code=403
            )
        
        access_token = create_access_token(data={"sub": str(user.id)})
        
        response = Response(headers={"Location": "/dashboard"}, status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
    except Exception as e:
        logger.error("login_error", error=str(e), email=email)
        return Response(
            content="<script>alert('Login failed. Please try again.'); window.history.back();</script>",
            media_type="text/html",
            status_code=500
        )

@router.post("/auth/logout")
async def logout():
    response = Response(headers={"Location": "/"}, status_code=303)
    response.delete_cookie("access_token")
    return response