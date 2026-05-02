from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.models.company import Company
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get(int(user_id))
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_company(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Company:
    """Get the company of current user (tenant context)"""
    company = await db.get(Company, current_user.company_id)
    if not company or not company.is_active:
        raise HTTPException(403, "Company is inactive or not found")
    return company


def require_roles(*roles: str):
    normalized = set()
    for r in roles:
        normalized.add(r.upper())
        normalized.add(r.lower())

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_role = (current_user.role or "").upper()
        allowed = {r.upper() for r in roles}
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker
