import restate

from app.db.postings import read_user_balance
from app.models.account import AccountBalance

account_service = restate.Service("account_service")


@account_service.handler()
async def get_balance(ctx: restate.Context, user_id: int) -> AccountBalance:
    # Journaled so a replay returns the balance this invocation actually read,
    # instead of re-querying and observing a different one.
    return await ctx.run_typed("read-balance", read_user_balance, user_id=user_id)
