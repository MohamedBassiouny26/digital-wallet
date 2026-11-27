"""Ledger postings: the DB side of a deposit or a transfer.

Plain async functions, deliberately free of any Restate `ctx` — each one is
invoked from a handler through a single `ctx.run_typed` step, and a step's
callback must not touch the context. Each function owns exactly one DB
transaction, so a posting's entries land together or not at all, and each is
idempotent on `transactions.idempotency_key` so that a re-run of the step
cannot post twice.
"""

from collections.abc import Sequence

from restate import TerminalError

from app.db.enums import Side
from app.db.models import Account
from app.db.repo import (
    create_entry,
    create_transaction,
    get_deposits_processing_accounts_by_user_id,
    get_transaction_id_by_idempotency_key,
    get_user_balance,
    get_users_accounts,
)
from app.db.seed import wallet_name
from app.db.session import session_scope
from app.models.account import AccountBalance
from app.models.entry import EntryCreate
from app.models.ledger import Side as EntrySide
from app.models.transactions import (
    DepositCreate,
    DepositResponse,
    TransactionCreate,
    TransactionKind,
    TransferCreate,
    TransferResponse,
)

CASH_ACCOUNT = "Cash"
FEES_ACCOUNT = "Card Processing Fees"

DEPOSIT_FEE_PERCENT = 2


class Operation:
    ADD = "add"
    SUBTRACT = "subtract"


def _account_by_name(accounts: Sequence[Account], name: str) -> Account:
    for account in accounts:
        if account.name == name:
            return account
    # A missing account is a chart-of-accounts problem; retrying cannot fix it.
    raise TerminalError(f"Account with name {name} not found")


def _side_for(account: Account, operation: str) -> EntrySide:
    """The entry side that moves `account` in `operation`'s direction.

    `EntrySide` rather than `db.enums.Side` because `EntryCreate` is modelled on
    the former; the two enums are identical but distinct types.
    """
    if account.normal_side == Side.DEBIT:
        return EntrySide.DEBIT if operation == Operation.ADD else EntrySide.CREDIT
    if account.normal_side == Side.CREDIT:
        return EntrySide.CREDIT if operation == Operation.ADD else EntrySide.DEBIT
    raise TerminalError(
        f"Invalid operation {operation} for account {account.name}"
    )


async def post_deposit(
    deposit: DepositCreate, idempotency_key: str
) -> DepositResponse:
    """Post a deposit: credit the user's wallet, debit Cash and the fee expense."""
    fees = deposit.amount * DEPOSIT_FEE_PERCENT // 100
    net_amount = deposit.amount - fees

    async with session_scope() as session:
        accounts = await get_deposits_processing_accounts_by_user_id(
            session, deposit.user_id
        )
        user_account = _account_by_name(accounts, wallet_name(user_id=deposit.user_id))
        cash_account = _account_by_name(accounts, CASH_ACCOUNT)
        fees_account = _account_by_name(accounts, FEES_ACCOUNT)

        transaction_id = await create_transaction(
            session,
            TransactionCreate(
                amount=deposit.amount,
                user_id=deposit.user_id,
                kind=TransactionKind.DEPOSIT,
                idempotency_key=idempotency_key,
            ),
        )
        if transaction_id is None:
            # Already posted — this is a re-run of the step, not a new deposit.
            transaction_id = await get_transaction_id_by_idempotency_key(
                session, idempotency_key
            )
            return DepositResponse(
                transaction_id=transaction_id,
                user_account_id=user_account.id,
                amount=deposit.amount,
            )

        await create_entry(
            session,
            EntryCreate(
                transaction_id=transaction_id,
                account_id=user_account.id,
                side=_side_for(user_account, Operation.ADD),
                amount=deposit.amount,
            ),
        )
        await create_entry(
            session,
            EntryCreate(
                transaction_id=transaction_id,
                account_id=fees_account.id,
                side=_side_for(fees_account, Operation.ADD),
                amount=fees,
            ),
        )
        await create_entry(
            session,
            EntryCreate(
                transaction_id=transaction_id,
                account_id=cash_account.id,
                side=_side_for(cash_account, Operation.ADD),
                amount=net_amount,
            ),
        )

    return DepositResponse(
        transaction_id=transaction_id,
        user_account_id=user_account.id,
        amount=deposit.amount,
    )


async def post_transfer(
    transfer: TransferCreate, idempotency_key: str
) -> TransferResponse:
    """Post a transfer: debit the sender's wallet, credit the recipient's."""
    async with session_scope() as session:
        accounts = await get_users_accounts(
            session, [transfer.from_user_id, transfer.to_user_id]
        )
        from_account = _account_by_name(
            accounts, wallet_name(user_id=transfer.from_user_id)
        )
        to_account = _account_by_name(
            accounts, wallet_name(user_id=transfer.to_user_id)
        )

        transaction_id = await create_transaction(
            session,
            TransactionCreate(
                amount=transfer.amount,
                user_id=transfer.from_user_id,
                kind=TransactionKind.TRANSFER,
                idempotency_key=idempotency_key,
            ),
        )
        if transaction_id is None:
            transaction_id = await get_transaction_id_by_idempotency_key(
                session, idempotency_key
            )
            return TransferResponse(
                transaction_id=transaction_id,
                from_user_account_id=from_account.id,
                to_user_account_id=to_account.id,
                amount=transfer.amount,
            )

        await create_entry(
            session,
            EntryCreate(
                transaction_id=transaction_id,
                account_id=from_account.id,
                side=_side_for(from_account, Operation.SUBTRACT),
                amount=transfer.amount,
            ),
        )
        await create_entry(
            session,
            EntryCreate(
                transaction_id=transaction_id,
                account_id=to_account.id,
                side=_side_for(to_account, Operation.ADD),
                amount=transfer.amount,
            ),
        )

    return TransferResponse(
        transaction_id=transaction_id,
        from_user_account_id=from_account.id,
        to_user_account_id=to_account.id,
        amount=transfer.amount,
    )


async def read_user_balance(user_id: int) -> AccountBalance:
    """Read a user's wallet balance in its own session."""
    async with session_scope() as session:
        return await get_user_balance(session, user_id)
