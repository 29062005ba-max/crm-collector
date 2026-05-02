from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.security import get_password_hash
from app.models.user import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def create_user(self, data: UserCreate) -> User:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        user = User(
            email=data.email,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role,
            hashed_password=get_password_hash(data.password),
        )
        return await self.repo.create(user)

    async def get_user(self, user_id: int) -> User:
        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = await self.get_user(user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        for field, value in update_data.items():
            setattr(user, field, value)
        return await self.repo.update(user)

    async def list_users(self) -> list[User]:
        return await self.repo.get_active_users()

    async def delete_user(self, user_id: int) -> None:
        user = await self.get_user(user_id)
        user.is_active = False
        await self.repo.update(user)
