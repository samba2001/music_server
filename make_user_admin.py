"""Utility script to mark a user as admin."""
import argparse
import asyncio
import os

from sqlalchemy import select

# Override the environment variable *before* importing database modules
# Update this path if your music_server.db is located elsewhere
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./music_server.db"

from app.core.database import AsyncSessionLocal, init_db
from app.models import User

DEFAULT_EMAIL = "sambasivareddykuluru@gmail.com"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a user as admin")
    parser.add_argument(
        "--email",
        type=str,
        default=DEFAULT_EMAIL,
        help="Email of the user to make admin",
    )
    args = parser.parse_args()

    await init_db()

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == args.email)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user is None:
            print(f"User with email '{args.email}' not found")
            return 1

        user.is_admin = True
        session.add(user)
        await session.commit()
        print(f"User {user.email} (id={user.id}) is now an admin")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)