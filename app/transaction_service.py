import restate

from app.db.enums import Side
from app.db.repo import create_transaction, get_deposits_processing_accounts_by_user_id
from app.db.seed import wallet_name
from app.db.session import session_scope
from app.models.entry import EntryCreate, EntryResponse
from app.db import create_entry as db_create_entry
from app.models.transactions import DepositCreate, DepositResponse, TransactionCreate, TransactionKind

transaction_service = restate.Service("transaction_service")



@transaction_service.handler()
async def deposit(ctx: restate.Context, deposit: DepositCreate) -> DepositResponse:
    # steps:
    # 1. get all neeeded accounts for the user - cash account and fees account
    # 2. create a transaction
    # 3. create an entry for the transaction
    # 4. fees (2% of the amount) will be deducted from the cash account and credited to the fees account
    # 5. create an entry for the cash account
    # 6. create an entry for the fees account
    idempotency_key = ctx.request().headers.get("idempotency-key")
    transaction = TransactionCreate(
            amount=deposit.amount,
            user_id=deposit.user_id,
            kind=TransactionKind.DEPOSIT,
            idempotency_key=idempotency_key or str(ctx.uuid())
    )
    # Minor units, integers only: a float fee breaks `entries.amount > 0` and
    # would leave debits and credits off by fractions of a cent.
    fees = deposit.amount * 2 // 100
    net_amount = deposit.amount - fees
    async with session_scope() as session:
        # get all needed accounts for the user - cash account and fees account
        accounts = await get_deposits_processing_accounts_by_user_id(session, deposit.user_id)
        # create transaction
        
        transaction_id = await create_transaction(session, transaction)

        # filter accounts by name
        user_account=__filter_account_by_name(accounts, wallet_name(user_id=deposit.user_id)) # credit account type
        cash_account=__filter_account_by_name(accounts, "Cash") # debit account type
        fees_account=__filter_account_by_name(accounts, "Card Processing Fees") # debit account type

        # add money to the user account
        await db_create_entry(session, EntryCreate(
            transaction_id=transaction_id, account_id=user_account.id, side=_get_direction_for_account(user_account, OperationEnum.ADD), amount=deposit.amount
        ))
        # add fees to the fees account
        await db_create_entry(session, EntryCreate(
            transaction_id=transaction_id, account_id=fees_account.id, side=_get_direction_for_account(fees_account, OperationEnum.ADD), amount=fees
        ))
        # add net amount to the cash account
        await db_create_entry(session, EntryCreate(
            transaction_id=transaction_id, account_id=cash_account.id, side=_get_direction_for_account(cash_account, OperationEnum.ADD), amount=net_amount
        ))
    return DepositResponse(transaction_id=transaction_id, user_account_id=user_account.id, amount=deposit.amount)


def __filter_account_by_name(accounts, name: str):
    for account in accounts:
        if account.name == name:
            return account
    raise ValueError(f"Account with name {name} not found")

class OperationEnum:
    ADD = "add"
    SUBTRACT = "subtract"

def _get_direction_for_account(account,operation:OperationEnum):
    if account.normal_side == "debit":
        if operation == OperationEnum.ADD:
            return Side.DEBIT
        elif operation == OperationEnum.SUBTRACT:
            return Side.CREDIT
    elif account.normal_side == "credit":
        if operation == OperationEnum.ADD:
            return Side.CREDIT
        elif operation == OperationEnum.SUBTRACT:
            return Side.DEBIT
    raise ValueError(f"Invalid operation {operation} for account {account.name}")