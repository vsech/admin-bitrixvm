from __future__ import annotations

import argparse
import asyncio
import getpass
import secrets
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password


async def create_admin(username: str, password: str) -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(User).where(User.username == username)):
            raise SystemExit(f"user {username!r} already exists")
        session.add(User(username=username, password_hash=hash_password(password)))
        await session.commit()
    print(f"Created administrator {username!r}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="bitrixvm-admin")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="create an administrator")
    create.add_argument("username")
    create.add_argument("--password-stdin", action="store_true")
    subparsers.add_parser("generate-secrets", help="print three deployment secrets")
    args = parser.parse_args()
    if args.command == "generate-secrets":
        for name in ("postgres_password", "master_key", "jwt_secret"):
            print(f"{name}={secrets.token_urlsafe(48)}")
        return
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            raise SystemExit("password stdin is empty")
    else:
        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("passwords do not match")
    if len(password) < 12:
        raise SystemExit("password must contain at least 12 characters")
    asyncio.run(create_admin(args.username, password))


if __name__ == "__main__":
    main()
