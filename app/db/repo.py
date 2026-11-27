from typing import List, Sequence

from sqlalchemy import insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Entry, Transaction
from app.db.seed import wallet_name
from app.models.entry import EntryCreate, EntryResponse

# The caller owns the transaction (see `session_scope`), so nothing here
# commits: a deposit's entries must land together or not at all.


async def create_entry(session: AsyncSession, entry: EntryCreate) -> EntryResponse:
    """Create a new entry in the database."""
    stmt = (
        insert(Entry)
        .values(
            transaction_id=entry.transaction_id,
            account_id=entry.account_id,
            direction=entry.side.value,
            amount=entry.amount,
        )
        .returning(Entry.id)
    )
    entry_id = (await session.execute(stmt)).scalar_one()
    return EntryResponse(
        id=entry_id,
        transaction_id=entry.transaction_id,
        account_id=entry.account_id,
        side=entry.side,
        amount=entry.amount,
    )


### Accounts
async def get_deposits_processing_accounts_by_user_id(
    session: AsyncSession, user_id: int
) -> Sequence[Account]:
    """The three accounts a deposit posts to: the user's wallet, Cash, and fees."""
    stmt = select(Account).where(
        or_(
            Account.user_id == user_id,
            Account.name.in_(("Cash", "Card Processing Fees")),
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


### Transactions
async def create_transaction(session: AsyncSession, transaction) -> int:
    """Create a new transaction in the database."""
    # Only the columns `transactions` actually has: amount and user_id live on
    # the entries, not on the transaction itself.
    stmt = (
        insert(Transaction)
        .values(
            kind=transaction.kind.value,
            idempotency_key=transaction.idempotency_key,
        )
        .returning(Transaction.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()
