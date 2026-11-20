from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin
from app.db.enums import AccountType, Side, TransactionKind


def _enum(python_enum: type, name: str) -> Enum:
    """TEXT column constrained by a CHECK, matching the SQL in the README."""
    return Enum(
        python_enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Account(CreatedAtMixin, Base):
    """A chart-of-accounts entry: Cash, Fee Revenue, or a per-user wallet."""

    __tablename__ = "accounts"
    __table_args__ = (
        # One wallet per user.
        Index(
            "uq_accounts_user_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        # House accounts (Cash, Fee Revenue, ...) are unique by name.
        Index(
            "uq_accounts_house_name",
            "name",
            unique=True,
            postgresql_where=text("user_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[AccountType] = mapped_column(
        _enum(AccountType, "account_type"), nullable=False
    )
    normal_side: Mapped[Side] = mapped_column(
        _enum(Side, "account_normal_side"), nullable=False
    )
    # Set for user wallets, NULL for house accounts (Cash, Fee Revenue, ...).
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class Transaction(CreatedAtMixin, Base):
    """A balanced group of entries posted atomically."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[TransactionKind] = mapped_column(
        _enum(TransactionKind, "transaction_kind"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)


class Entry(CreatedAtMixin, Base):
    """One leg of a transaction. Append-only: never update or delete an entry."""

    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_entries_amount_positive"),
        Index("ix_entries_account_id", "account_id"),
        Index("ix_entries_transaction_id", "transaction_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("transactions.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=False
    )
    direction: Mapped[Side] = mapped_column(
        _enum(Side, "entry_direction"), nullable=False
    )
    # Minor units (piasters/cents) — integers only, never floats.
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
