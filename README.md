# Ledger Project — Simple Digital Wallet

## Technologies

- **Restate** — durable execution for transaction workflows (deposits, transfers, withdrawals), with retries and idempotency
- **PostgreSQL** — ledger storage (accounts, transactions, entries)
- **Python / FastAPI** — API and application logic

## Product Scope

- View wallet account balances
- Add funds via card or bank
- Send money to other users
- Withdraw balance into a bank account
- Pay a fee on withdrawal

**Goals**
- Ensure the sum of all user balances reconciles with cash in our bank (see invariant below)
- Calculate revenue from fees

---

## Chart of Accounts

| Account | Meaning | Type | Normal side |
|---|---|---|---|
| Cash | Total cash held by the wallet company | Asset | Debit |
| User Wallet (per user) | Cash held on behalf of a user | Liability | Credit |
| Card Processing Fees | Transaction expenses paid to processor | Expense | Debit |
| Fee Revenue | Revenue from fees charged to users | Revenue | Credit |
| Owner Equity *(add)* | Capital that covers shortfalls (e.g. absorbed fees) | Equity | Credit |

---

## Key Transactions

### 1. Transfer — User A sends 100 to User B

| Account | Debit | Credit |
|---|---|---|
| A Wallet | 100 | |
| B Wallet | | 100 |

Debiting A's wallet reduces what we owe A. Crediting B's wallet increases what we owe B.

### 2. Deposit — User A deposits 300 by card (2% processing fee absorbed by us)

| Account | Debit | Credit |
|---|---|---|
| Cash | 294 | |
| Card Processing Fees | 6 | |
| A Wallet | | 300 |

Balanced: 294 + 6 = 300.

### 3. Withdrawal — User A withdraws 100 with a 2 fee on top

| Account | Debit | Credit |
|---|---|---|
| A Wallet | 102 | |
| Cash | | 100 |
| Fee Revenue | | 2 |

> Decide early whether the fee is **on top** (user needs 102) or **deducted** (user receives 98). This changes the balance check.

---

## Invariants

1. **Every transaction is balanced:** sum of debits = sum of credits.
2. **Accounting equation:**

   ```
   Cash = Σ User Wallets + Fee Revenue − Expenses + Owner Equity
   ```

   ⚠️ "Sum of user balances = cash in bank" alone does **not** hold. After the deposit above, users are owed 300 but we hold 294. The 6 gap is the absorbed expense and must be covered by revenue or owner equity.

3. **No user wallet goes negative.**

---

## Database Modeling

```sql
CREATE TABLE accounts (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('asset','liability','equity','revenue','expense')),
    normal_side  TEXT NOT NULL CHECK (normal_side IN ('debit','credit')),
    user_id      BIGINT NULL,          -- set for user wallets
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transactions (
    id               BIGSERIAL PRIMARY KEY,
    kind             TEXT NOT NULL CHECK (kind IN ('deposit','transfer','withdrawal')),
    idempotency_key  TEXT NOT NULL UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entries (
    id              BIGSERIAL PRIMARY KEY,
    transaction_id  BIGINT NOT NULL REFERENCES transactions(id),
    account_id      BIGINT NOT NULL REFERENCES accounts(id),
    direction       TEXT NOT NULL CHECK (direction IN ('debit','credit')),
    amount          BIGINT NOT NULL CHECK (amount > 0),   -- minor units (piasters/cents)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON entries (account_id);
CREATE INDEX ON entries (transaction_id);
```

### Balance query

```sql
SELECT a.id,
       SUM(CASE WHEN e.direction = a.normal_side THEN e.amount ELSE -e.amount END) AS balance
FROM accounts a
JOIN entries e ON e.account_id = a.id
WHERE a.id = :account_id
GROUP BY a.id;
```

---

## Application Logic Rules

- **Balanced check:** validate debits = credits before commit, all inside one DB transaction.
- **Append-only:** never update or delete entries. Fix mistakes with a reversing transaction.
- **Overdraft protection:** `SELECT ... FOR UPDATE` on the sender's wallet, then check its balance before posting.
- **Deadlock avoidance:** in transfers, lock both accounts in ascending account id order.
- **Integers only:** store money in minor units, never floats.
- **Idempotency:** a unique idempotency key per request prevents double-posting on retries.
- **(Later) Cached balances:** keep a `balance` column on accounts, updated in the same DB transaction as the entries, for fast reads.

---

## Verification

- Replay all entries: total debits = total credits.
- Check the accounting equation holds.
- Reconcile the Cash account against the real bank statement.
- Tests: concurrent transfers from the same wallet, retried requests with the same idempotency key, a withdrawal exceeding balance.