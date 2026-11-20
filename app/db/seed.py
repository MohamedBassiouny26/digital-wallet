"""Seed the chart of accounts: the house accounts plus one wallet per user.

Idempotent — re-running only inserts what is missing. Run with:

    python -m app.db.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AccountType, Side
from app.db.models import Account
from app.db.session import session_scope

# (name, type, normal_side) for the accounts in the README's chart of accounts.
HOUSE_ACCOUNTS: tuple[tuple[str, AccountType, Side], ...] = (
    ("Cash", AccountType.ASSET, Side.DEBIT),
    ("Card Processing Fees", AccountType.EXPENSE, Side.DEBIT),
    ("Fee Revenue", AccountType.REVENUE, Side.CREDIT),
)

FIRST_USER_ID = 1
LAST_USER_ID = 100


def wallet_name(user_id: int) -> str:
    return f"User {user_id} Wallet"


async def seed_accounts(
    session: AsyncSession,
    first_user_id: int = FIRST_USER_ID,
    last_user_id: int = LAST_USER_ID,
) -> list[Account]:
    """Insert any missing house accounts and user wallets. Returns what was added."""
    existing_house = set(
        (
            await session.scalars(select(Account.name).where(Account.user_id.is_(None)))
        ).all()
    )
    existing_wallets = set(
        (
            await session.scalars(
                select(Account.user_id).where(Account.user_id.is_not(None))
            )
        ).all()
    )

    added = [
        Account(name=name, type=type_, normal_side=normal_side)
        for name, type_, normal_side in HOUSE_ACCOUNTS
        if name not in existing_house
    ]
    added += [
        Account(
            name=wallet_name(user_id),
            # A wallet is cash we hold on behalf of a user, so we owe it to them.
            type=AccountType.LIABILITY,
            normal_side=Side.CREDIT,
            user_id=user_id,
        )
        for user_id in range(first_user_id, last_user_id + 1)
        if user_id not in existing_wallets
    ]

    session.add_all(added)
    await session.flush()
    return added


async def main() -> None:
    async with session_scope() as session:
        added = await seed_accounts(session)
    print(f"seeded {len(added)} account(s)")


if __name__ == "__main__":
    asyncio.run(main())
