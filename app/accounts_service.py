import restate

from app.db.enums import Side
from app.db.repo import create_transaction, get_deposits_processing_accounts_by_user_id, get_user_balance
from app.db.seed import wallet_name
from app.db.session import session_scope
from app.models.account import AccountBalance
from app.models.entry import EntryCreate, EntryResponse
from app.db import create_entry as db_create_entry
from app.models.transactions import DepositCreate, DepositResponse, TransactionCreate, TransactionKind

account_service = restate.Service("account_service")



@account_service.handler()
async def get_balance(ctx: restate.Context, user_id: int) -> AccountBalance:
    async with session_scope() as session:
        return await get_user_balance(session, user_id)
