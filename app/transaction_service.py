import restate

from app.db.postings import post_deposit, post_transfer
from app.models.transactions import (
    DepositCreate,
    DepositResponse,
    TransferCreate,
    TransferResponse,
)

transaction_service = restate.Service("transaction_service")


def _idempotency_key(ctx: restate.Context) -> str:
    """A key that is stable across every replay and re-run of this invocation.

    `ctx.uuid()` is journaled, so a retried invocation reuses the same key and
    the posting's ON CONFLICT turns the second attempt into a no-op.
    """
    return ctx.request().headers.get("idempotency-key") or str(ctx.uuid())


@transaction_service.handler()
async def deposit(ctx: restate.Context, req: DepositCreate) -> DepositResponse:
    # One durable step for the whole posting: the transaction row and all three
    # entries share a DB transaction, so Restate can never journal a partial,
    # unbalanced deposit.
    return await ctx.run_typed(
        "post-deposit",
        post_deposit,
        deposit=req,
        idempotency_key=_idempotency_key(ctx),
    )


@transaction_service.handler()
async def transfer(ctx: restate.Context, req: TransferCreate) -> TransferResponse:
    return await ctx.run_typed(
        "post-transfer",
        post_transfer,
        transfer=req,
        idempotency_key=_idempotency_key(ctx),
    )
