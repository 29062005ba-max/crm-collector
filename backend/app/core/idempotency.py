"""Idempotency-Key support for critical endpoints"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enterprise import IdempotencyKey


def hash_request(method: str, path: str, body: Any) -> str:
    """SHA256 от метода+пути+тела для проверки что идемпотентный ключ относится к тому же запросу"""
    payload = f"{method}:{path}:{json.dumps(body, sort_keys=True, default=str)}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def check_idempotency(
    db: AsyncSession,
    request: Request,
    body: Any = None,
    user_id: int | None = None,
    company_id: int | None = None,
) -> tuple[Optional[IdempotencyKey], Optional[str]]:
    """
    Проверка наличия Idempotency-Key в заголовке.
    Возвращает (existing_record, key) если запрос уже выполнялся,
    или (None, key) если новый запрос (нужно сохранить результат после),
    или (None, None) если ключ не передан.
    """
    key = request.headers.get("Idempotency-Key")
    if not key:
        return None, None

    # Validate key format
    if len(key) > 128 or len(key) < 8:
        raise HTTPException(400, "Idempotency-Key must be 8-128 chars")

    request_hash = hash_request(request.method, request.url.path, body)

    result = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Verify same request body — иначе это conflict
        if existing.request_hash != request_hash:
            raise HTTPException(
                409,
                "Idempotency-Key conflict: key was used with different request body"
            )
        # Verify not expired
        if existing.expires_at < datetime.utcnow():
            # Старая запись — игнорируем
            return None, key
        return existing, key

    return None, key


async def save_idempotency_response(
    db: AsyncSession,
    key: str,
    request: Request,
    body: Any,
    response: Any,
    status: int = 200,
    user_id: int | None = None,
    company_id: int | None = None,
    ttl_hours: int = 24,
) -> None:
    """Сохранить результат после успешного выполнения"""
    record = IdempotencyKey(
        key=key,
        endpoint=f"{request.method} {request.url.path}",
        user_id=user_id,
        company_id=company_id,
        request_hash=hash_request(request.method, request.url.path, body),
        response_status=status,
        response_body=response if isinstance(response, dict) else {"value": str(response)},
        expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
    )
    db.add(record)
    await db.flush()
