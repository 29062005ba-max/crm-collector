#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
async def check():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text('SELECT 1'))
        return True
    except:
        return False
import asyncio
result = asyncio.run(check())
sys.exit(0 if result else 1)
" 2>/dev/null; do
  echo "PostgreSQL not ready, retrying in 2s..."
  sleep 2
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Ensuring default company exists..."
python3 - << 'PYEOF'
import asyncio, sys
sys.path.insert(0, '/app')
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        # Ensure default company (id=1) exists
        result = await db.execute(text("SELECT id FROM companies WHERE id=1"))
        exists = result.scalar_one_or_none()
        if not exists:
            await db.execute(text("""
                INSERT INTO companies (id, name, slug, tariff, max_users, max_debtors, is_active, contact_email, created_at, updated_at)
                VALUES (1, 'Default Company', 'default', 'enterprise', 100, 100000, true, 'admin@crm.local', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """))
            # Reset sequence
            await db.execute(text("SELECT setval('companies_id_seq', GREATEST((SELECT MAX(id) FROM companies), 1), true)"))
            await db.commit()
            print("Default company created (id=1)")
        else:
            print("Default company already exists")

asyncio.run(main())
PYEOF

echo "Creating/updating default admin user..."
python3 - << 'PYEOF'
import asyncio, bcrypt, sys
sys.path.insert(0, '/app')
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    h = bcrypt.hashpw(b'Admin1234!', bcrypt.gensalt(10)).decode()
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT id, company_id FROM users WHERE email='admin@crm.local'"))
        row = result.first()
        if not row:
            # Create new admin in default company
            await db.execute(text("""
                INSERT INTO users (email, full_name, hashed_password, role, is_active, company_id, created_at, updated_at)
                VALUES ('admin@crm.local', 'Administrator', :h, 'ADMIN', true, 1, NOW(), NOW())
            """), {"h": h})
            print("Admin created in company_id=1")
        else:
            # Update existing - reset password and ensure company_id=1
            await db.execute(text(
                "UPDATE users SET hashed_password=:h, company_id=COALESCE(company_id, 1) WHERE email='admin@crm.local'"
            ), {"h": h})
            print(f"Admin password updated (company_id={row[1] or 1})")
        await db.commit()
        print("Login: admin@crm.local / Admin1234!")

asyncio.run(main())
PYEOF

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
