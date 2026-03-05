"""
CLI script to bootstrap the first admin user.

Usage:
    python scripts/create_superuser.py --email admin@example.com --password secret
"""
import argparse
import asyncio
import sys

sys.path.insert(0, ".")  # run from project root

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from sqlalchemy import select


async def create_superuser(email: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            print(f"User {email!r} already exists.")
            return

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Admin",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        print(f"Admin user created: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(create_superuser(args.email, args.password))
