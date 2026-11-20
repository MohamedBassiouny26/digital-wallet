from enum import StrEnum


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class Side(StrEnum):
    """Which side of the ledger: an account's normal side, or an entry's direction."""

    DEBIT = "debit"
    CREDIT = "credit"


class TransactionKind(StrEnum):
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
