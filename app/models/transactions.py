



import enum

from pydantic import BaseModel, ConfigDict

from app.models.ledger import Side


class DepositCreate(BaseModel):
    amount: int
    user_id: int

class DepositResponse(BaseModel):
    transaction_id: int
    user_account_id: int
    amount: int

    model_config = ConfigDict(from_attributes=True)
class TransactionKind(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"

class TransactionCreate(BaseModel):
    amount: int
    user_id: int
    kind:TransactionKind
    idempotency_key: str