"""Utility script to mark a user as admin and ensure DB column exists.

Usage:
  - Edit DEFAULT_EMAIL below and run without args:
      python -m scripts.make_user_admin
  - Or pass flags:
      python -m scripts.make_user_admin --email user@example.com
      python -m scripts.make_user_admin --id 123

This script will:
 - call `init_db()` to create tables if missing
 - ensure `is_admin` column exists on `users` (runs ALTER if needed)
 - find the user by email or id and set `is_admin = True`
"""
import argparse
import asyncio
from typing import Optional

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal, init_db, engine
from app.models import User

# Edit this if you want a default email when running without args
DEFAULT_EMAIL: Optional[str] = "sambasivareddykuluru@gmail.com"


async def ensure_is_admin_column(session):
    try:
        dialect = engine.dialect.name
        if dialect == "sqlite":
            res = await session.execute(text("PRAGMA table_info('users')"))
            cols = [row[1] for row in res.all()]
            if "is_admin" not in cols:
                await session.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
                await session.commit()
        else:
            res = await session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin'"))
            exists = len(res.all()) > 0
            if not exists:
                default = "false" if dialect.startswith("postgres") else "0"
                await session.execute(text(f"ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT {default}"))
                await session.commit()
    except Exception:
        # don't fail the whole script for migration issues
        pass


async def main(email: Optional[str], id_value: Optional[str]) -> int:
    # Ensure database tables are created (calls Base.metadata.create_all)
    await init_db()

    async with AsyncSessionLocal() as session:
        # Ensure is_admin column exists
        await ensure_is_admin_column(session)

        if id_value:
            stmt = select(User).where(User.id == int(id_value))
        else:
            stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user is None:
            print("User not found")
            return 1
        user.is_admin = True
        session.add(user)
        await session.commit()
        print(f"User {user.email} (id={user.id}) is now an admin")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mark a user as admin")
    parser.add_argument("--email", help="Email address of the user", default=None)
    parser.add_argument("--id", help="Numeric id of the user", default=None)
    args = parser.parse_args()

    email_to_use = args.email or DEFAULT_EMAIL
    id_to_use = args.id

    if not email_to_use and not id_to_use:
        print("No email or id provided and DEFAULT_EMAIL is not set. Edit the script or pass --email/--id.")
        raise SystemExit(2)

    raise SystemExit(asyncio.run(main(email_to_use, id_to_use)))
