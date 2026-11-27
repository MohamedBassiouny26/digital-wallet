



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

class TransferCreate(BaseModel):
    amount: int
    from_user_id: int
    to_user_id: int

class TransferResponse(BaseModel):
    transaction_id: int
    from_user_account_id: int
    to_user_account_id: int
    amount: int

    model_config = ConfigDict(from_attributes=True)

class WithdrawCreate(BaseModel):
    amount: int
    user_id: int
class WithdrawResponse(BaseModel):
    amount: int
    fees: int
    transaction_id: int


